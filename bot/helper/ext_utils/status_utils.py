from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall, sub as re_sub
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory

from ... import (
    DOWNLOAD_DIR,
    bot_cache,
    bot_start_time,
    status_dict,
    task_dict,
    task_dict_lock,
)
from ...core.config_manager import Config
from ..telegram_helper.button_build import ButtonMaker
from ..telegram_helper.emoji import e, icon, label as btn_label

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOAD = "Upload"
    STATUS_DOWNLOAD = "Download"
    STATUS_CLONE = "Clone"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVE = "Archive"
    STATUS_EXTRACT = "Extract"
    STATUS_SPLIT = "Split"
    STATUS_CHECK = "CheckUp"
    STATUS_SEED = "Seed"
    STATUS_SAMVID = "SamVid"
    STATUS_CONVERT = "Convert"
    STATUS_FFMPEG = "FFmpeg"
    STATUS_YT = "YouTube"
    STATUS_METADATA = "Metadata"
    STATUS_SEEDR = "Seedr"


STATUS_ICONS = {
    MirrorStatus.STATUS_DOWNLOAD: "download",
    MirrorStatus.STATUS_UPLOAD: "upload",
    MirrorStatus.STATUS_SEED: "upload",
    MirrorStatus.STATUS_CLONE: "folder",
    MirrorStatus.STATUS_PAUSED: "clock",
    MirrorStatus.STATUS_QUEUEDL: "clock",
    MirrorStatus.STATUS_QUEUEUP: "clock",
    MirrorStatus.STATUS_YT: "video",
    MirrorStatus.STATUS_ARCHIVE: "folder",
    MirrorStatus.STATUS_EXTRACT: "folder",
    MirrorStatus.STATUS_SPLIT: "edit",
    MirrorStatus.STATUS_FFMPEG: "video",
    MirrorStatus.STATUS_CONVERT: "video",
}


class EngineStatus:
    def __init__(self):
        ver = bot_cache.get("eng_versions", {})
        self.STATUS_ARIA2 = f"Aria2 v{ver.get('aria2', 'N/A')}"
        self.STATUS_AIOHTTP = f"AioHttp v{ver.get('aiohttp', 'N/A')}"
        self.STATUS_GDAPI = f"Google-API v{ver.get('gapi', 'N/A')}"
        self.STATUS_QBIT = f"qBit v{ver.get('qBittorrent', 'N/A')}"
        self.STATUS_TGRAM = f"WzPyro v{ver.get('wzgram', 'N/A')}"
        self.STATUS_MEGA = f"MegaSDK v{ver.get('mega', 'N/A')}"
        self.STATUS_YTDLP = f"yt-dlp v{ver.get('yt-dlp', 'N/A')}"
        self.STATUS_GALLERYDL = f"gallery-dl v{ver.get('gallery-dl', 'N/A')}"
        self.STATUS_TLDV = "tl;dv"
        self.STATUS_FFMPEG = f"ffmpeg v{ver.get('ffmpeg', 'N/A')}"
        self.STATUS_7Z = f"7z v{ver.get('7z', 'N/A')}"
        self.STATUS_RCLONE = f"RClone v{ver.get('rclone', 'N/A')}"
        self.STATUS_SABNZBD = f"SABnzbd+ v{ver.get('SABnzbd+', 'N/A')}"
        self.STATUS_QUEUE = "QSystem v2"
        self.STATUS_JD = "JDownloader v2"
        self.STATUS_YT = "Youtube-Api"
        self.STATUS_METADATA = "Metadata"
        self.STATUS_UPHOSTER = "Uphoster"
        self.STATUS_SEEDR = "Seedr"


STATUSES = {
    "ALL": "All",
    "DL": MirrorStatus.STATUS_DOWNLOAD,
    "UP": MirrorStatus.STATUS_UPLOAD,
    "QD": MirrorStatus.STATUS_QUEUEDL,
    "QU": MirrorStatus.STATUS_QUEUEUP,
    "AR": MirrorStatus.STATUS_ARCHIVE,
    "EX": MirrorStatus.STATUS_EXTRACT,
    "SD": MirrorStatus.STATUS_SEED,
    "CL": MirrorStatus.STATUS_CLONE,
    "CM": MirrorStatus.STATUS_CONVERT,
    "SP": MirrorStatus.STATUS_SPLIT,
    "SV": MirrorStatus.STATUS_SAMVID,
    "FF": MirrorStatus.STATUS_FFMPEG,
    "PA": MirrorStatus.STATUS_PAUSED,
    "CK": MirrorStatus.STATUS_CHECK,
}


async def get_task_by_gid(gid: str):
    async with task_dict_lock:
        for tk in task_dict.values():
            if hasattr(tk, "seeding"):
                await tk.update()
            if tk.gid() == gid or tk.gid().startswith(gid):
                return tk
        return None


async def get_specific_tasks(status, user_id):
    if status == "All":
        if user_id:
            return [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        else:
            return list(task_dict.values())
    tasks_to_check = (
        [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        if user_id
        else list(task_dict.values())
    )
    coro_tasks = []
    coro_tasks.extend(tk for tk in tasks_to_check if iscoroutinefunction(tk.status))
    coro_statuses = await gather(*[tk.status() for tk in coro_tasks])
    result = []
    coro_index = 0
    for tk in tasks_to_check:
        if tk in coro_tasks:
            st = coro_statuses[coro_index]
            coro_index += 1
        else:
            st = tk.status()
        if (st == status) or (
            status == MirrorStatus.STATUS_DOWNLOAD and st not in STATUSES.values()
        ):
            result.append(tk)
    return result


async def get_all_tasks(req_status: str, user_id):
    async with task_dict_lock:
        return await get_specific_tasks(req_status, user_id)


def get_raw_file_size(size):
    num, unit = size.split()
    return int(float(num) * (1024 ** SIZE_UNITS.index(unit)))


def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0B"
    if size_in_bytes < 0:
        return "Unknown"

    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1

    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds: int):
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result


def get_raw_time(time_str: str) -> int:
    time_units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(
        int(value) * time_units[unit]
        for value, unit in findall(r"(\d+)([dhms])", time_str)
    )


def time_to_seconds(time_duration):
    try:
        parts = time_duration.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = map(float, parts)
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = float(parts[0])
        else:
            return 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


def speed_string_to_bytes(size_text: str):
    size = 0
    size_text = size_text.lower()
    if "k" in size_text:
        size += float(size_text.split("k")[0]) * 1024
    elif "m" in size_text:
        size += float(size_text.split("m")[0]) * 1048576
    elif "g" in size_text:
        size += float(size_text.split("g")[0]) * 1073741824
    elif "t" in size_text:
        size += float(size_text.split("t")[0]) * 1099511627776
    elif "b" in size_text:
        size += float(size_text.split("b")[0])
    return size


def get_progress_bar_string(pct):
    pct = float(str(pct).strip("%"))
    filled = round(min(max(pct, 0), 100) / 10)
    return "▰" * filled + "▱" * (10 - filled)


class StatusText(str):
    """Status HTML; .rich holds the rich message version when one was built."""

    rich = None
    keep_markup = False


UPLOAD_NAMES = {"Leech": "Telegram", "GDrive": "Google Drive", "RClone": "Rclone"}


def upload_text(mode):
    """'#Leech (Zip)' -> 'Telegram as Zip', with the source: 'from GDrive'."""
    dest, _, extra = mode[1].lstrip("#").partition(" (")
    text = UPLOAD_NAMES.get(dest, dest)
    if extra:
        text += f" as {extra.rstrip(')')}"
    return f"{text} <i>(from {mode[0].lstrip('#')})</i>"


async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    msg = ""
    button = None

    tasks = await get_specific_tasks(status, sid if is_user else None)

    STATUS_LIMIT = Config.STATUS_LIMIT
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
        status_dict[sid]["page_no"] = page_no
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
        status_dict[sid]["page_no"] = page_no
    start_position = (page_no - 1) * STATUS_LIMIT

    from ..telegram_helper.bot_commands import BotCommands

    rich_tasks = []
    shown = len(tasks[start_position : STATUS_LIMIT + start_position])
    if tasks_no:
        msg += f"{e('list')} <b>Tasks:</b> {shown}/{tasks_no}"
        if pages > 1:
            msg += f"  ·  <b>Page:</b> {page_no}/{pages}  ·  <b>Step:</b> {page_step}"
        msg += "\n\n"
    for index, task in enumerate(
        tasks[start_position : STATUS_LIMIT + start_position], start=1
    ):
        if status != "All":
            tstatus = status
        elif iscoroutinefunction(task.status):
            tstatus = await task.status()
        else:
            tstatus = task.status()
        listener = task.listener
        user = listener.message.from_user
        elapsed = get_readable_time(time() - listener.message.date.timestamp())
        title = f"{index + start_position}. {tstatus}"
        icon_name = STATUS_ICONS.get(tstatus, "gear")
        bar = pct = None
        fields = []
        if (
            tstatus not in [MirrorStatus.STATUS_SEED, MirrorStatus.STATUS_QUEUEUP]
            and listener.progress
        ):
            pct = task.progress()
            bar = get_progress_bar_string(pct)
            subsize = (
                f" / {get_readable_file_size(listener.subsize)}"
                if listener.subname
                else ""
            )
            fields += [
                ("Processed", f"{task.processed_bytes()}{subsize}"),
                ("Size", task.size()),
                ("Speed", task.speed()),
                ("ETA", task.eta()),
            ]
            if listener.subname:
                ac = len(listener.files_to_proceed)
                fields.append(("Files", f"{listener.proceed_count} / {ac or '?'}"))
            if tstatus == MirrorStatus.STATUS_DOWNLOAD and (
                listener.is_torrent or listener.is_qbit
            ):
                try:
                    fields.append(
                        ("Peers", f"{task.seeders_num()} seeders · {task.leechers_num()} leechers")
                    )
                except Exception:
                    pass
        elif tstatus == MirrorStatus.STATUS_SEED:
            fields += [
                ("Size", task.size()),
                ("Uploaded", task.uploaded_bytes()),
                ("Speed", task.seed_speed()),
                ("Ratio", task.ratio()),
                ("Seeding", task.seeding_time()),
            ]
        else:
            fields.append(("Size", task.size()))
        upload = upload_text(listener.mode)
        fields += [("Elapsed", elapsed), ("Upload", upload), ("Engine", task.engine)]
        can_select = tstatus in [
            MirrorStatus.STATUS_DOWNLOAD,
            MirrorStatus.STATUS_PAUSED,
            MirrorStatus.STATUS_QUEUEDL,
        ] and (listener.is_torrent or listener.is_qbit or listener.is_nzb)
        gid = task.gid()[:8]

        msg += f"{e(icon_name)} <b>{title}</b>\n"
        rows = [f"<i>{escape(f'{task.name()}')}</i>"]
        if listener.subname:
            rows.append(f"<i>↳ {escape(listener.subname)}</i>")
        if bar:
            rows.append(f"{bar} <b>{pct}</b>")
        rows += [f"<b>{k}:</b> {v}" for k, v in fields]
        by = f"<b>User:</b> {user.mention(style='html')} (<code>{user.id}</code>)"
        if listener.is_super_chat:
            by += f" · <a href='{listener.message.link}'>Link</a>"
        rows.append(by)
        msg += "<blockquote>" + "\n".join(rows) + "</blockquote>\n"
        cmds = []
        if can_select:
            cmds.append(f"Select /{BotCommands.SelectCommand[1]}_{gid}")
        cmds.append(f"Stop /{BotCommands.CancelTaskCommand[1]}_{gid}")
        msg += f"{e('close')} " + "  ·  ".join(cmds) + "\n\n"
        rich_tasks.append(
            {
                "icon": icon_name,
                "title": title,
                "name": task.name(),
                "sub": listener.subname,
                "bar": bar,
                "pct": pct,
                "fields": [(k, re_sub(r"<[^>]+>", "", str(v))) for k, v in fields],
                "user": (getattr(user, "first_name", None) or "User", user.id),
                "select": can_select,
                "gid": gid,
            }
        )

    if len(msg) == 0:
        if status == "All":
            return None, None
        else:
            msg = f"{e('info')} No active <b>{status}</b> tasks.\n\n"

    buttons = ButtonMaker()
    buttons.data_button(
        btn_label("bolt", "Refresh"),
        f"status {sid} ref",
        position="header",
        icon=icon("bolt"),
    )
    if len(tasks) > STATUS_LIMIT:
        buttons.data_button(
            btn_label("prev", "Prev"), f"status {sid} pre", position="header", icon=icon("prev")
        )
        buttons.data_button(
            btn_label("next", "Next"), f"status {sid} nex", position="header", icon=icon("next")
        )
        if tasks_no > 30:
            for i in [1, 2, 4, 6, 8, 10, 15]:
                buttons.data_button(i, f"status {sid} ps {i}", position="footer")
    if status != "All" or tasks_no > 20:
        for label, status_value in list(STATUSES.items()):
            if status_value != status:
                buttons.data_button(label, f"status {sid} st {status_value}")
    button = buttons.build_menu(8)
    free = disk_usage(DOWNLOAD_DIR)
    cpu, ram = cpu_percent(), virtual_memory().percent
    free_text = get_readable_file_size(free.free)
    uptime = get_readable_time(time() - bot_start_time)
    msg += (
        f"{e('chart')} <b>Bot Stats</b>\n"
        f"<blockquote><b>CPU:</b> {cpu}% | <b>FREE:</b> {free_text}\n"
        f"<b>RAM:</b> {ram}% | <b>UPTIME:</b> {uptime}</blockquote>"
    )
    msg = StatusText(msg)
    if rich_tasks and Config.RICH_STATUS:
        from .status_rich import build_rich_status

        header = f"Tasks: {shown}/{tasks_no}"
        if pages > 1:
            header += f"  ·  Page {page_no}/{pages}"
        try:
            nav = [("bolt", "Refresh", f"status {sid} ref")]
            if len(tasks) > STATUS_LIMIT:
                nav = [
                    ("prev", "Prev", f"status {sid} pre"),
                    *nav,
                    ("next", "Next", f"status {sid} nex"),
                ]
            msg.rich = build_rich_status(
                header,
                rich_tasks,
                [
                    [("CPU", f"{cpu}%"), ("FREE", free_text)],
                    [("RAM", f"{ram}%"), ("UPTIME", uptime)],
                ],
                nav,
            )
            # filters/step buttons have no in-text version: keep the keyboard then
            msg.keep_markup = tasks_no > 20 or status != "All"
        except Exception as err:
            from ... import LOGGER

            LOGGER.error(f"Rich status build failed, using HTML: {err}")
    return msg, button
