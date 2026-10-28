from ast import literal_eval

from gallery_dl import extractor

from .. import DOWNLOAD_DIR, LOGGER, bot_loop, task_dict_lock
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import COMMAND_USAGE, arg_parser, safe_path_name
from ..helper.ext_utils.links_utils import is_url
from ..helper.ext_utils.task_manager import pre_task_check
from ..helper.listeners.task_listener import TaskListener
from ..helper.mirror_leech_utils.download_utils.gallery_dl_download import (
    GalleryDLHelper,
    sanitize_gallery_dl_options,
)
from ..helper.telegram_helper.error_report import report_task_error
from ..helper.telegram_helper.message_utils import (
    auto_delete_message,
    delete_links,
    send_message,
)


def _is_gallery_dl_link(link):
    try:
        return extractor.find(link) is not None
    except Exception:
        return False


class GalleryDL(TaskListener):
    def __init__(
        self,
        client,
        message,
        is_leech=False,
        same_dir=None,
        bulk=None,
        multi_tag=None,
        options="",
        **kwargs,
    ):
        if same_dir is None:
            same_dir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multi_tag = multi_tag
        self.options = options
        self.same_dir = same_dir
        self.bulk = bulk
        super().__init__()
        self.is_gallerydl = True
        self.is_leech = is_leech

    async def new_event(self):
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")

        check_msg, check_button = await pre_task_check(self.message)
        if check_msg:
            await delete_links(self.message)
            await auto_delete_message(
                await send_message(self.message, check_msg, check_button)
            )
            return

        args = {
            "-doc": False,
            "-med": False,
            "-b": False,
            "-z": False,
            "-sv": False,
            "-ss": False,
            "-f": False,
            "-fd": False,
            "-fu": False,
            "-hl": False,
            "-bt": False,
            "-ut": False,
            "-i": 0,
            "-sp": 0,
            "link": "",
            "-m": "",
            "-meta": "",
            "-opt": {},
            "-n": "",
            "-up": "",
            "-ud": "",
            "-gc": "",
            "-rcf": "",
            "-t": "",
            "-ca": "",
            "-cv": "",
            "-ns": "",
            "-tl": "",
            "-ff": set(),
        }

        arg_parser(input_list[1:], args)

        if Config.DISABLE_FF_MODE and args.get("-ff"):
            await send_message(self.message, "FFmpeg commands are currently disabled.")
            return

        try:
            self.multi = int(args["-i"])
        except Exception:
            self.multi = 0

        try:
            if args["-ff"]:
                if isinstance(args["-ff"], set):
                    self.ffmpeg_cmds = args["-ff"]
                else:
                    value = literal_eval(args["-ff"])
                    if not isinstance(value, (dict, set, list, tuple)):
                        raise ValueError("ffmpeg_cmds must be a dict/set/list/tuple")
                    self.ffmpeg_cmds = value
        except Exception as e:
            self.ffmpeg_cmds = None
            LOGGER.error(e)

        try:
            opt = literal_eval(args["-opt"]) if args["-opt"] else {}
            if not isinstance(opt, dict):
                raise ValueError("gallery-dl options must be a dict")
        except Exception as e:
            LOGGER.error(e)
            opt = {}

        self.name = args["-n"]
        self.up_dest = args["-up"]
        self.dump_dest = args["-ud"]
        self.category = args["-gc"]
        self.rc_flags = args["-rcf"]
        self.link = args["link"]
        self.compress = args["-z"]
        self.thumb = args["-t"]
        self.split_size = args["-sp"]
        self.sample_video = args["-sv"]
        self.screen_shots = args["-ss"]
        self.force_run = args["-f"]
        self.force_download = args["-fd"]
        self.force_upload = args["-fu"]
        self.convert_audio = args["-ca"]
        self.convert_video = args["-cv"]
        self.name_swap = args["-ns"]
        self.hybrid_leech = args["-hl"]
        self.thumbnail_layout = args["-tl"]
        self.as_doc = args["-doc"]
        self.as_med = args["-med"]
        self.folder_name = f"/{folder}" if (folder := safe_path_name(args["-m"])) else ""
        self.bot_trans = args["-bt"]
        self.user_trans = args["-ut"]
        self.metadata_dict = self.default_metadata_dict.copy()
        self.audio_metadata_dict = self.audio_metadata_dict.copy()
        self.video_metadata_dict = self.video_metadata_dict.copy()
        self.subtitle_metadata_dict = self.subtitle_metadata_dict.copy()
        if meta := args["-meta"]:
            self.metadata_dict = self.metadata_processor.merge_dicts(
                self.default_metadata_dict, self.metadata_processor.parse_string(meta)
            )

        is_bulk = args["-b"]

        bulk_start = 0
        bulk_end = 0

        if not isinstance(is_bulk, bool):
            dargs = is_bulk.split(":")
            bulk_start = dargs[0] or None
            if len(dargs) == 2:
                bulk_end = dargs[1] or None
            is_bulk = True

        if not is_bulk:
            if self.multi > 0:
                if self.folder_name:
                    async with task_dict_lock:
                        if self.folder_name in self.same_dir:
                            self.same_dir[self.folder_name]["tasks"].add(self.mid)
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        elif self.same_dir:
                            self.same_dir[self.folder_name] = {
                                "total": self.multi,
                                "tasks": {self.mid},
                            }
                            for fd_name in self.same_dir:
                                if fd_name != self.folder_name:
                                    self.same_dir[fd_name]["total"] -= 1
                        else:
                            self.same_dir = {
                                self.folder_name: {
                                    "total": self.multi,
                                    "tasks": {self.mid},
                                }
                            }
                elif self.same_dir:
                    async with task_dict_lock:
                        for fd_name in self.same_dir:
                            self.same_dir[fd_name]["total"] -= 1
        else:
            await self.init_bulk(input_list, bulk_start, bulk_end, GalleryDL)
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        path = f"{DOWNLOAD_DIR}{self.mid}{self.folder_name}"

        await self.get_tag(text)

        if opt := opt or self.user_dict.get("GALLERY_DL_OPTIONS"):
            if self.user_id != Config.OWNER_ID:
                opt = sanitize_gallery_dl_options(opt)
        else:
            opt = Config.GALLERY_DL_OPTIONS

        if not self.link and (reply_to := self.message.reply_to_message):
            if reply_to.text:
                self.link = reply_to.text.split("\n", 1)[0].strip()

        if not is_url(self.link):
            await send_message(
                self.message, COMMAND_USAGE["gdl"][0], COMMAND_USAGE["gdl"][1]
            )
            await self.remove_from_same_dir()
            await delete_links(self.message)
            return

        if not _is_gallery_dl_link(self.link):
            await send_message(
                self.message, f"{self.tag} This link is not supported by gallery-dl."
            )
            await self.remove_from_same_dir()
            await delete_links(self.message)
            return

        try:
            await self.before_start()
        except Exception as e:
            await report_task_error(self, e)
            await self.remove_from_same_dir()
            await delete_links(self.message)
            return

        self._set_mode_engine()

        await self.run_multi(input_list, GalleryDL)

        LOGGER.info(f"Downloading with gallery-dl: {self.link}")
        await GalleryDLHelper(self).add_download(path, opt)
        await delete_links(self.message)


async def gallery_dl(client, message):
    if Config.DISABLE_GALLERYDL:
        await message.reply("gallery-dl downloads are currently disabled by the Bot Owner.")
        return
    bot_loop.create_task(GalleryDL(client, message).new_event())


async def gallery_dl_leech(client, message):
    if Config.DISABLE_GALLERYDL:
        await message.reply("gallery-dl downloads are currently disabled by the Bot Owner.")
        return
    bot_loop.create_task(GalleryDL(client, message, is_leech=True).new_event())
