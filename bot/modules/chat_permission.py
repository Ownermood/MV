from time import time

from html import escape

from pyrogram.enums import ChatType

from .. import user_data
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import update_user_ldata, new_task
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.emoji import e
from ..helper.telegram_helper.rich_name import split_name_and_id
from ..helper.ext_utils.db_handler import database
from ..helper.telegram_helper.message_utils import send_message


def _parse_time(time_str):
    time_str = time_str.strip().lower()
    mult = {"d": 86400, "h": 3600, "m": 60}
    for suffix, factor in mult.items():
        if time_str.endswith(suffix):
            try:
                return int(time_str[: -len(suffix)]) * factor
            except ValueError:
                return None
    return None


def _format_remaining(seconds):
    if seconds >= 86400:
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        return f"{d}d {h}h" if h else f"{d}d"
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m" if m else f"{h}h"
    m = seconds // 60
    return f"{m}m"


def _get_blacklist_info(bl_value):
    if not bl_value:
        return False, None
    if bl_value is True:
        return True, "Permanent"
    if isinstance(bl_value, (int, float)):
        remaining = bl_value - time()
        if remaining > 0:
            return True, _format_remaining(int(remaining))
        return False, None
    return False, None


async def _target(message):
    """(name html, chat/user id, topic id) from '/cmd Name ID', '/cmd ID|topic',
    '/cmd @username' or a reply; id is None when nothing usable was given."""
    name, ref = split_name_and_id(message)
    if ref.startswith("@"):
        try:
            found = await TgClient.bot.get_users(ref)
        except Exception:
            try:
                found = await TgClient.bot.get_chat(ref)
            except Exception:
                return name, None, None
        return name or escape(getattr(found, "first_name", "") or ""), found.id, None
    if ref:
        chat, _, topic = ref.partition("|")
        return name, int(chat), int(topic) if topic.isdigit() else None
    reply = message.reply_to_message
    if reply and reply.id != message.message_thread_id:
        who = reply.from_user or reply.sender_chat
        default = escape(getattr(who, "first_name", None) or getattr(who, "title", "") or "")
        return name or default, who.id, None
    return name, None, None


def _usage(cmd, what):
    return (
        f"{e('info')} <b>How to use /{cmd}</b>\n"
        f"<blockquote><code>/{cmd} Name UserID</code>\n"
        f"e.g. <code>/{cmd} Wifu 8494053059</code>\n"
        f"or reply to their message with <code>/{cmd} Name</code></blockquote>\n"
        f"<i>The name is optional and may contain premium emoji. {what}</i>"
    )


@new_task
async def authorize(_, message):
    """/adduser: allow a user, or a group (no ID in a group = this group)."""
    from .admin_panel import allow_user

    name, chat_id, thread_id = await _target(message)
    if chat_id is None:
        if message.chat.type == ChatType.PRIVATE:
            return await send_message(message, _usage(BotCommands.AuthorizeCommand[0], "They can then use the bot anywhere."))
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat.id
    data = user_data.get(chat_id, {})
    if data.get("AUTH") and (thread_id is None or thread_id in data.get("thread_ids", [])):
        if name and chat_id > 0:
            update_user_ldata(chat_id, "PANEL_NAME", name)
            await database.update_user_data(chat_id)
        return await send_message(message, f"{e('done')} Already allowed.")
    if data.get("AUTH") and thread_id is not None:
        user_data[chat_id].setdefault("thread_ids", []).append(thread_id)
        await database.update_user_data(chat_id)
    else:
        if thread_id is not None:
            update_user_ldata(chat_id, "thread_ids", [thread_id])
        await allow_user(chat_id, name if chat_id > 0 else "")
    who = "This group" if chat_id < 0 else f"<b>{name or chat_id}</b>"
    await send_message(message, f"{e('done')} {who} can use the bot now.")


@new_task
async def unauthorize(_, message):
    """/rmuser: remove a user, a group, or one topic of a group."""
    from .admin_panel import disallow_user

    _, chat_id, thread_id = await _target(message)
    if chat_id is None:
        if message.chat.type == ChatType.PRIVATE:
            return await send_message(message, _usage(BotCommands.UnAuthorizeCommand[0], "They can then no longer use the bot."))
        if message.is_topic_message:
            thread_id = message.message_thread_id
        chat_id = message.chat.id
    data = user_data.get(chat_id, {})
    if not data.get("AUTH"):
        return await send_message(message, f"{e('info')} Not allowed anyway.")
    if thread_id and thread_id in data.get("thread_ids", []):
        data["thread_ids"].remove(thread_id)
        if data["thread_ids"]:
            await database.update_user_data(chat_id)
            return await send_message(message, f"{e('done')} Topic removed.")
    await disallow_user(chat_id)
    await send_message(message, f"{e('done')} Removed. They can no longer use the bot.")


@new_task
async def add_sudo(_, message):
    """/addadmin Name ID (or reply): make someone an admin; they get a DM."""
    from .admin_panel import add_admin

    name, user_id, _ = await _target(message)
    if user_id is None or user_id <= 0:
        return await send_message(message, _usage(BotCommands.AddSudoCommand[0], "They should /start the bot first to get the DM."))
    if user_data.get(user_id, {}).get("SUDO"):
        if name:
            update_user_ldata(user_id, "PANEL_NAME", name)
            await database.update_user_data(user_id)
            return await send_message(message, f"{e('done')} Already an admin. Name updated to <b>{name}</b>.")
        return await send_message(message, f"{e('done')} Already an admin.")
    await add_admin(user_id, name)
    await send_message(message, f"{e('party')} <b>{name or user_id}</b> is now an admin. They got a DM.")


@new_task
async def remove_sudo(_, message):
    """/rmadmin ID (or reply): remove an admin; they get a DM."""
    from .admin_panel import remove_admin

    _, user_id, _ = await _target(message)
    if user_id is None:
        return await send_message(message, _usage(BotCommands.RmSudoCommand[0], "The name is not needed here."))
    if await remove_admin(user_id):
        return await send_message(message, f"{e('done')} Admin removed. They got a DM.")
    await send_message(
        message,
        f"{e('info')} Not an admin here. The owner, and admins listed in config.py, can only be changed in config.py.",
    )


@new_task
async def add_blacklist(_, message):
    msg = message.text.split()
    id_ = None
    time_str = None

    i = 1
    while i < len(msg):
        arg = msg[i].lower()
        if arg.startswith("-t") and len(arg) > 2:
            time_str = arg[2:]
            i += 1
        elif arg == "-t" and i + 1 < len(msg):
            time_str = msg[i + 1]
            i += 2
        else:
            try:
                id_ = int(msg[i])
            except ValueError:
                pass
            i += 1

    if id_ is None and message.reply_to_message:
        id_ = (
            message.reply_to_message.from_user or message.reply_to_message.sender_chat
        ).id

    if id_ is None:
        help_msg = f"""{e('blocked')} <b>BlackList Usage</b>
<blockquote><b>Permanent:</b> <code>/bl {{user_id}}</code>
<b>Temporary:</b> <code>/bl {{user_id}} -t 1d</code>
<b>Reply:</b> <code>/bl -t 2h</code> <i>(reply to user)</i>
<b>Time Format:</b> <code>3d</code> | <code>12h</code> | <code>20m</code> <i>(any digit)</i></blockquote>"""
        return await send_message(message, help_msg)

    if id_ in user_data and _get_blacklist_info(user_data[id_].get("BLACKLIST"))[0]:
        return await send_message(
            message, f"<b>User Already BlackListed!</b> \u2192 <code>{id_}</code>"
        )

    if time_str:
        seconds = _parse_time(time_str)
        if seconds is None:
            return await send_message(
                message,
                "<b>Invalid Time Format!</b> Use <code>1d</code>, <code>2h</code>, or <code>30m</code>.",
            )
        bl_value = time() + seconds
        remaining = _format_remaining(seconds)
        update_user_ldata(id_, "BLACKLIST", bl_value)
        await database.update_user_data(id_)
        msg = f"""{e('blocked')} <b>BlackList Applied</b>
<blockquote><b>User</b> \u2192 <code>{id_}</code>
<b>Type</b> \u2192 <b>Temporary</b>
<b>Duration</b> \u2192 <code>{remaining}</code>
<b>Expires</b> \u2192 <b>{remaining} from now</b></blockquote>"""
    else:
        update_user_ldata(id_, "BLACKLIST", True)
        await database.update_user_data(id_)
        msg = f"""{e('blocked')} <b>BlackList Applied</b>
<blockquote><b>User</b> \u2192 <code>{id_}</code>
<b>Type</b> \u2192 <b>Permanent</b>
<b>Status</b> \u2192 <i>Restricted from Bot</i></blockquote>"""

    await send_message(message, msg)


@new_task
async def remove_blacklist(_, message):
    msg = message.text.split()
    id_ = None

    if len(msg) > 1:
        try:
            id_ = int(msg[1].strip())
        except ValueError:
            pass
    if id_ is None and message.reply_to_message:
        id_ = (
            message.reply_to_message.from_user or message.reply_to_message.sender_chat
        ).id

    if id_ is None:
        return await send_message(
            message,
            "Give ID or Reply To message of whom you want to remove from blacklist",
        )

    bl_value = user_data.get(id_, {}).get("BLACKLIST")
    is_bl, remaining = _get_blacklist_info(bl_value)
    if not is_bl:
        return await send_message(
            message, f"<b>User Already Freed</b> \u2192 <code>{id_}</code>"
        )

    update_user_ldata(id_, "BLACKLIST", False)
    await database.update_user_data(id_)
    await send_message(
        message,
        f"""{e('blocked')} <b>BlackList Removed</b>
<blockquote><b>User</b> \u2192 <code>{id_}</code>
<b>Status</b> \u2192 <i>User Set Free!</i></blockquote>""",
    )


@new_task
async def black_listed(_, message):
    await send_message(
        message, "<b>BlackListed Detected</b> \u2192 <i>Restricted from Bot</i>"
    )
