from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall
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
        elapsed = time() - listener.message.date.timestamp()
        msg += f"{e(STATUS_ICONS.get(tstatus, 'gear'))} <b>{index + start_position}. {escape(f'{task.name()}')}</b>"
        if listener.subname:
            msg += f"\n<i>↳ {escape(listener.subname)}</i>"
        rows = []
        if (
            tstatus not in [MirrorStatus.STATUS_SEED, MirrorStatus.STATUS_QUEUEUP]
            and listener.progress
        ):
            progress = task.progress()
            rows.append(f"{get_progress_bar_string(progress)}  <b>{progress}</b>")
            subsize = (
                f" / {get_readable_file_size(listener.subsize)}"
                if listener.subname
                else ""
            )
            rows.append(
                f"<b>{tstatus}</b> · {task.processed_bytes()}{subsize} of {task.size()}"
            )
            if listener.subname:
                ac = len(listener.files_to_proceed)
                rows.append(f"<b>Files:</b> {listener.proceed_count} / {ac or '?'}")
            rows.append(
                f"{e('bolt')} {task.speed()}  ·  {e('clock')} {task.eta()} left"
                f"  ·  {get_readable_time(elapsed)} gone"
            )
            if tstatus == MirrorStatus.STATUS_DOWNLOAD and (
                listener.is_torrent or listener.is_qbit
            ):
                try:
                    rows.append(
                        f"{e('globe')} Seeders {task.seeders_num()} · Leechers {task.leechers_num()}"
                    )
                except Exception:
                    pass
        elif tstatus == MirrorStatus.STATUS_SEED:
            rows.append(
                f"<b>{tstatus}</b> · {task.size()} · uploaded {task.uploaded_bytes()}"
            )
            rows.append(f"{e('bolt')} {task.seed_speed()}  ·  Ratio {task.ratio()}")
            rows.append(
                f"{e('clock')} Seeding {task.seeding_time()}  ·  {get_readable_time(elapsed)} gone"
            )
        else:
            rows.append(f"<b>{tstatus}</b> · {task.size()}")
        rows.append(
            f"{e('gear')} {task.engine}  ·  {listener.mode[0]} → {listener.mode[1]}"
        )
        by = f"{e('users')} {user.mention(style='html')} · <code>{user.id}</code>"
        if listener.is_super_chat:
            by += f" · <a href='{listener.message.link}'>Link</a>"
        rows.append(by)
        msg += "\n<blockquote>" + "\n".join(rows) + "</blockquote>\n"
        if tstatus in [
            MirrorStatus.STATUS_DOWNLOAD,
            MirrorStatus.STATUS_PAUSED,
            MirrorStatus.STATUS_QUEUEDL,
        ] and (listener.is_torrent or listener.is_qbit or listener.is_nzb):
            msg += f"{e('list')} Select: /{BotCommands.SelectCommand[1]}_{task.gid()[:8]}\n"
        msg += f"{e('close')} Stop: /{BotCommands.CancelTaskCommand[1]}_{task.gid()[:8]}\n\n"

    if len(msg) == 0:
        if status == "All":
            return None, None
        else:
            msg = f"{e('info')} No active <b>{status}</b> tasks.\n\n"

    buttons = ButtonMaker()
    if not is_user:
        buttons.data_button(
            btn_label("chart", "Stats"),
            f"status {sid} ov",
            position="header",
            icon=icon("chart"),
        )
    buttons.data_button(
        btn_label("bolt", "Refresh"),
        f"status {sid} ref",
        position="header",
        icon=icon("bolt"),
    )
    if len(tasks) > STATUS_LIMIT:
        msg += f"{e('list')} <b>Page</b> {page_no}/{pages} · <b>Tasks</b> {tasks_no} · <b>Step</b> {page_step}\n"
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
    msg += (
        f"{e('chart')} <b>Bot Stats</b>\n"
        f"<blockquote>{e('server')} CPU {cpu_percent()}%  ·  RAM {virtual_memory().percent}%\n"
        f"{e('folder')} Free {get_readable_file_size(free.free)} ({round(100 - free.percent, 1)}%)"
        f"  ·  {e('clock')} Up {get_readable_time(time() - bot_start_time)}</blockquote>"
    )
    return msg, button
