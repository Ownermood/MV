# Where a task's error goes: the full text to the user's DM and to
# ERROR_LOG_CHAT; the group where the task was started stays clean and only
# gets a short reason when the DM could not be delivered.
from html import escape
from re import sub

from pyrogram.enums import ChatType

from ... import LOGGER
from ...core.config_manager import Config
from .emoji import e
from .message_utils import send_message

# known errors -> plain words for the user
FRIENDLY_ERRORS = (
    ("cannotDownloadFile", "The Drive owner has blocked downloads for this file."),
    ("fileNotDownloadable", "This Google file can't be downloaded."),
    ("downloadQuotaExceeded", "Google's download limit for this file is reached. Try again later."),
    ("userRateLimitExceeded", "Google rate limit reached. Try again in a while."),
    ("storageQuotaExceeded", "The destination Drive is full."),
    ("File not found", "File not found, or not shared with the bot's Google account."),
    ("notFound", "File not found, or not shared with the bot's Google account."),
    ("Google Drive is not set up", "Google Drive is not set up on this bot yet."),
    ("NO TOKEN", "Google Drive is not set up on this bot yet."),
    ("Sign in to confirm", "YouTube is blocking the bot's server. The owner needs to add YouTube cookies."),
    ("confirm your age", "This video is age-restricted. The owner needs to add YouTube cookies."),
    ("Private video", "This video is private."),
    ("Video unavailable", "This video is unavailable."),
    ("Unsupported URL", "This link is not supported."),
    ("Requested format is not available", "That quality/format is not available for this video."),
)


def plain(error):
    return " ".join(sub(r"<[^>]+>", " ", str(error)).split())


def short_reason(error):
    text = plain(error)
    for key, nice in FRIENDLY_ERRORS:
        if key.casefold() in text.casefold():
            return nice
    return text if len(text) <= 160 else text[:157] + "…"


def chat_ref(value):
    value = str(value or "").strip()
    if not value:
        return None
    return int(value) if value.lstrip("-").isdigit() else value


def _who(listener):
    if tag := getattr(listener, "tag", ""):
        return tag
    user = listener.message.from_user or listener.message.sender_chat
    return getattr(user, "mention", None) or escape(getattr(user, "title", "") or "")


def _in_group(listener):
    return listener.message.chat.type != ChatType.PRIVATE


async def report_error(listener, full, short, button=None):
    """full/short: ready HTML. Full goes to the log chat and the user's DM."""
    message = listener.message
    log_chat = chat_ref(Config.ERROR_LOG_CHAT)
    if log_chat and log_chat not in (message.chat.id, message.chat.username):
        link = f"\n<a href='{message.link}'>Task message</a>" if _in_group(listener) else ""
        sent = await send_message(log_chat, full + link)
        if isinstance(sent, str):
            LOGGER.warning(f"ERROR_LOG_CHAT {log_chat} not reachable (make the bot admin there): {sent}")
    elif log_chat:
        LOGGER.warning("ERROR_LOG_CHAT is the task's own chat; full errors are not posted there")
    if not _in_group(listener):
        # started in DM: the DM is the task's chat
        return await send_message(message, full, button)
    sent = await send_message(listener.user_id, full, button)
    if isinstance(sent, str):
        # the user never started the bot: tell them in the group, briefly
        await send_message(message, short, button)


async def report_task_error(listener, error, button=None, title="Task Stopped"):
    """For errors before or around a task (bad link, limits, yt-dlp, …)."""
    who = _who(listener)
    link = getattr(listener, "link", "") or ""
    full = (
        f"{e('warn')} <b>{title}</b>\n<blockquote>"
        + (f"<b>Link:</b> {escape(link[:300])}\n" if link else "")
        + f"<b>Reason:</b> {escape(plain(error))}\n<b>User:</b> {who}</blockquote>"
    )
    short = (
        f"{e('warn')} <b>{title}</b>\n<blockquote><b>Reason:</b> {escape(short_reason(error))}\n"
        f"<b>User:</b> {who}</blockquote>\n<i>Start the bot in DM to get full details there.</i>"
    )
    await report_error(listener, full, short, button)
