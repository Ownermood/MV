"""Leech of a folder tree uploads folder by folder: a Section message, that
folder's files in order, then an Uploaded message; also with parallel upload."""
import asyncio, importlib.util, os, sys, tempfile, types

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


class Cfg:
    PREMIUM_EMOJI = False; LEECH_SECTIONS = True; USE_HYPER = False; BOT_PM = False
    MEDIA_GROUP = False; LEECH_PREFIX = LEECH_SUFFIX = LEECH_CAPTION = LEECH_FONT = ""


events = []


async def send_message(chat_id, text, message_thread_id=None, disable_notification=None):
    events.append(("msg", chat_id, text))


async def flood(func, *a, **k): return await func(*a, **k)


async def sync_to_async(func, *a): return func(*a)


mod("bot"); mod("bot.core"); mod("bot.core.config_manager", Config=Cfg)
mod("bot.core.tg_client", TgClient=types.SimpleNamespace(bot=types.SimpleNamespace(send_message=send_message), user=None))
mod("bot.helper"); mod("bot.helper.ext_utils"); mod("bot.helper.telegram_helper")
mod("bot.helper.ext_utils.bot_utils", sync_to_async=sync_to_async)
mod("bot.helper.ext_utils.files_utils", get_base_name=None, is_archive=None)
mod("bot.helper.ext_utils.status_utils", get_readable_file_size=str, get_readable_time=str)
mod("bot.helper.ext_utils.media_utils", get_md5_hash=None, get_media_info=None)
mod("bot.helper.ext_utils.hyperul_utils", HypertgUpload=object)
mod("bot.helper.telegram_helper.message_utils", delete_message=None)
mod("bot.helper.telegram_helper.tg_copy", call_with_flood_retry=flood)
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.upload_utils")
for name, path in (("bot.helper.telegram_helper.emoji", "bot/helper/telegram_helper/emoji.py"),
                   ("bot.helper.mirror_leech_utils.upload_utils.telegram_uploader",
                    "bot/helper/mirror_leech_utils/upload_utils/telegram_uploader.py")):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
tu = sys.modules["bot.helper.mirror_leech_utils.upload_utils.telegram_uploader"]


class Up(tu.TelegramUploader):
    async def _user_settings(self): pass
    async def _msg_to_reply(self): return True
    async def _upload_file_task(self, file_, f_path, dirpath, user_session, seq_idx):
        # later files finish first under parallel upload, like real uploads
        await asyncio.sleep(0.01 * (5 - int(file_[0])))
        events.append(("file", os.path.basename(dirpath), file_))
        self._upload_seq[seq_idx] = {"link": file_, "file_": file_, "chat_id": 1, "msg_id": 1}
        return True
    async def _sequence_copies(self, src_chat): pass


class Listener:
    thumb = None; user_id = 5; transmission_mode = "bot"; is_cancelled = False
    up_dest = 5; chat_thread_id = None; name = "Course"
    message = types.SimpleNamespace(chat=types.SimpleNamespace(id=-100))
    async def on_upload_complete(self, *a): events.append(("complete",))
    async def on_upload_error(self, err): events.append(("error", err))


ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)


def expected(dirs):
    out = []
    for i, d in enumerate(dirs, 1):
        out.append(("start", d))
        out += [("file", d, f"{n}.mp4") for n in (1, 2, 3)]
        out.append(("end", d))
    return out


def simplify(evts):
    out = []
    for ev in evts:
        if ev[0] == "msg":
            assert ev[1] == 5, "section messages go to the upload chat (user DM)"
            kind = "end" if "uploaded" in ev[2] else "start"
            out.append((kind, ev[2].split(": ", 1)[1].split("<")[0]))
        elif ev[0] == "file":
            out.append(ev)
    return out


with tempfile.TemporaryDirectory() as work:
    root = f"{work}/Course"
    for d in ("D", "B", "A", "C"):
        os.makedirs(f"{root}/{d}")
        for n in (3, 1, 2):
            open(f"{root}/{d}/{n}.mp4", "wb").write(b"x")
    for hyper in (False, True):
        Cfg.USE_HYPER = hyper; events.clear()
        asyncio.run(Up(Listener(), root).upload())
        got = simplify(events)
        if hyper:
            # parallel: files of a section may finish in any order, but never
            # outside their own section's start/end messages
            norm, block = [], []
            for ev in got:
                if ev[0] == "file":
                    block.append(ev)
                else:
                    norm += sorted(block) + [ev]; block = []
            got = norm
        t(f"sections A-D in order, each folder's files inside its section (parallel={hyper})", got == expected("ABCD"))
        t(f"end note counts files (parallel={hyper})", all("3/3" in ev[2] for ev in events if ev[0] == "msg" and "uploaded" in ev[2]))
        t(f"task completes once (parallel={hyper})", events[-1] == ("complete",))
    Cfg.LEECH_SECTIONS = False; events.clear()
    asyncio.run(Up(Listener(), root).upload())
    t("LEECH_SECTIONS off: no section messages", not any(ev[0] == "msg" for ev in events))
    Cfg.LEECH_SECTIONS = True
    single = f"{work}/One"; os.makedirs(single)
    for n in (1, 2): open(f"{single}/{n}.mp4", "wb").write(b"x")
    events.clear(); asyncio.run(Up(Listener(), single).upload())
    t("single folder: no section messages", not any(ev[0] == "msg" for ev in events))
print("ALL PASS" if ok else "SOME FAILED")
