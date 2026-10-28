# Force join: users must join the configured channels/groups before using the bot.
# Chats come from FORCE_SUB_CHATS (set in /admin: id, button name, join link) plus
# the older FORCE_SUB_IDS (ids only; name and link are read from the chat).
from asyncio import gather
from html import escape
from time import time

from pyrogram.enums import ButtonStyle
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.filters import create

from ... import LOGGER
from ...core.config_manager import Config
from .button_build import ButtonMaker
from .emoji import e, icon, label
from .filters import CustomFilters
from .tg_utils import chat_info

JOINED_TTL = 600
_joined_until = {}
# uid -> join prompt message, edited to the welcome menu once the user joins
pending_prompts = {}


def clear_join_cache():
    _joined_until.clear()


def forget_user(user_id):
    _joined_until.pop(user_id, None)


def fsub_chats():
    chats, seen = [], set()
    for item in Config.FORCE_SUB_CHATS if isinstance(Config.FORCE_SUB_CHATS, list) else []:
        if isinstance(item, dict) and str(item.get("id", "")).strip():
            chats.append(
                {
                    "id": str(item["id"]).strip(),
                    "name": str(item.get("name") or ""),
                    "link": str(item.get("link") or ""),
                }
            )
            seen.add(chats[-1]["id"])
    for cid in str(Config.FORCE_SUB_IDS or "").split():
        if cid not in seen:
            chats.append({"id": cid, "name": "", "link": ""})
    return chats


async def _missing_one(chat, user_id):
    info = await chat_info(chat["id"])
    if info is None:
        LOGGER.warning(f"Force join: bot cannot access {chat['id']}, not enforcing it")
        return None
    try:
        await info.get_member(user_id)
        return None
    except UserNotParticipant:
        link = chat["link"] or (
            f"https://t.me/{info.username}" if info.username else info.invite_link
        )
        return chat["name"] or info.title or "Join", link
    except RPCError as err:
        # usually the bot is not an admin there; never lock users out because of it
        LOGGER.warning(f"Force join check failed for {chat['id']}: {err.MESSAGE}")
    except Exception as err:
        LOGGER.warning(f"Force join check failed for {chat['id']}: {err}")
    return None


async def missing_chats(user_id, use_cache=True):
    """(name, link) for every configured chat the user has not joined."""
    chats = fsub_chats()
    if not chats:
        return []
    if use_cache and _joined_until.get(user_id, 0) > time():
        return []
    missing = [m for m in await gather(*(_missing_one(c, user_id) for c in chats)) if m]
    if missing:
        _joined_until.pop(user_id, None)
    else:
        _joined_until[user_id] = time() + JOINED_TTL
    return missing


def join_markup(user_id, missing):
    buttons = ButtonMaker()
    for name, link in missing:
        if link:
            buttons.url_button(label("add", name), link, style=ButtonStyle.SUCCESS, icon=icon("add"))
    return buttons.build_menu(1)


def join_text(missing):
    rows = "\n".join(f"{e('link')} <b>{escape(name)}</b>" for name, _ in missing)
    return (
        f"{e('warn')} <b>Join required</b>\n\n"
        f"To use <b>Mirror Leech Villan Bot</b>, please join:\n{rows}\n\n"
        f"{e('done')} You are verified <b>automatically</b> as soon as you join."
    )


async def _not_joined(_, __, update):
    sender = update.from_user or update.sender_chat
    if sender is None or not fsub_chats():
        return False
    if await CustomFilters.sudo("", update):
        return False
    return bool(await missing_chats(sender.id))


not_joined = create(_not_joined)
