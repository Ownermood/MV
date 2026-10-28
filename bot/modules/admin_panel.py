# /admin: control panel for the welcome screen, force join, broadcast and premium emoji.
from asyncio import Event, TimeoutError as AsyncTimeout, wait_for
from html import escape
from time import time

from pyrogram.enums import ChatMemberStatus
from pyrogram.filters import private, user
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from .. import bot_start_time, task_dict
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import new_task
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.telegram_helper.button_build import ButtonMaker, valid_url
from ..helper.telegram_helper.emoji import EMOJI, e, icon, label
from ..helper.telegram_helper.force_join import clear_join_cache, fsub_chats
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)
from ..helper.telegram_helper.prompt import STOP, PromptUnreachable, ask_in_pm
from ..helper.telegram_helper.tg_utils import chat_info
from .broadcast import run_broadcast
from .services import start_home, start_photo

LINE = "━━━━━━━━━━━━━━━━━━"
pending_broadcast = {}


async def _save(key, value):
    Config.set(key, value)
    if key.startswith("FORCE_SUB"):
        clear_join_cache()
    if Config.DATABASE_URL:
        await database.update_config({key: value})


def _cb(uid, action, arg=""):
    return f"adm {uid} {action} {arg}".strip()


def _btn(buttons, uid, name, text, action, arg="", position=None):
    buttons.data_button(label(name, text), _cb(uid, action, arg), position, icon=icon(name))


def _onoff(flag):
    return f"{e('on')} ON" if flag else f"{e('off')} OFF"


async def _wait_pm(uid, timeout=120):
    """Next private message from uid (any type), or None on timeout."""
    event, box = Event(), [None]

    async def on_msg(_, message):
        box[0] = message
        event.set()

    handler = TgClient.bot.add_handler(
        MessageHandler(on_msg, filters=user(uid) & private), group=-1
    )
    try:
        await wait_for(event.wait(), timeout)
    except AsyncTimeout:
        pass
    finally:
        TgClient.bot.remove_handler(*handler)
    return box[0]


async def _ask(uid, body):
    try:
        reply = await ask_in_pm(uid, body)
    except PromptUnreachable:
        return None, "Start the bot in private chat first, then try again."
    if reply in (None, STOP):
        return None, None
    return reply, None


# ---------- pages ----------


async def _home(uid):
    try:
        users = len(await database.get_pm_uids()) if Config.DATABASE_URL else "N/A"
    except Exception:
        users = "N/A"
    text = f"""{e("gem")} <b>ADMIN PANEL</b> — <i>Mirrorleach Villanbot</i>
{LINE}
{e("users")} <b>Users:</b> <code>{users}</code>
{e("chart")} <b>Running tasks:</b> <code>{len(task_dict)}</code>
{e("clock")} <b>Uptime:</b> <code>{get_readable_time(time() - bot_start_time)}</code>
{e("star")} <b>Premium emoji:</b> {_onoff(Config.PREMIUM_EMOJI)}
{e("key")} <b>Force join chats:</b> <code>{len(fsub_chats())}</code>
{LINE}
<i>Changes apply instantly and are saved.</i>"""
    b = ButtonMaker()
    _btn(b, uid, "wave", "Welcome Text", "text")
    _btn(b, uid, "image", "Welcome Image", "img")
    _btn(b, uid, "link", "Start Buttons", "btns")
    _btn(b, uid, "key", "Force Join", "fj")
    _btn(b, uid, "mail", "Broadcast", "bc")
    _btn(b, uid, "gem", "Premium Emoji", "prem")
    _btn(b, uid, "search", "Preview /start", "preview")
    _btn(b, uid, "gear", "All Settings", "settings")
    _btn(b, uid, "close", "Close", "close", position="footer")
    return text, b.build_menu(2)


def _back(b, uid, to="home"):
    _btn(b, uid, "back", "Back", to, position="footer")


async def _text_page(uid, note=""):
    current = (
        f"<blockquote>{escape(Config.START_TEXT[:600])}</blockquote>"
        if Config.START_TEXT
        else "<i>Built-in text (bot description + quick start).</i>"
    )
    text = f"""{e("wave")} <b>Welcome Text</b>
{LINE}
Shown under the greeting when someone sends /start.
You can use bold, italic, links and premium emoji — just format your message in Telegram.

<b>Current:</b>
{current}{note}"""
    b = ButtonMaker()
    _btn(b, uid, "edit", "Edit Text", "text_set")
    if Config.START_TEXT:
        _btn(b, uid, "trash", "Use Built-in", "text_reset")
    _back(b, uid)
    return text, b.build_menu(2)


async def _img_page(uid, note=""):
    if Config.START_IMAGE:
        current = f"{e('done')} Custom image set"
    elif Config.USE_IMAGES and Config.IMAGES:
        current = f"{e('image')} Random image from IMAGES"
    else:
        current = f"{e('off')} No image (text only)"
    text = f"""{e("image")} <b>Welcome Image</b>
{LINE}
Photo sent with /start.

<b>Current:</b> {current}{note}"""
    b = ButtonMaker()
    _btn(b, uid, "image", "Set Image", "img_set")
    if Config.START_IMAGE:
        _btn(b, uid, "trash", "Remove", "img_reset")
    _back(b, uid)
    return text, b.build_menu(2)


async def _btns_page(uid, note=""):
    links = Config.START_LINKS if isinstance(Config.START_LINKS, dict) else {}
    rows = "\n".join(
        f"{i}. {escape(str(k))} → <code>{escape(str(v))}</code>"
        for i, (k, v) in enumerate(links.items(), 1)
    ) or "<i>None — one Updates button to AUTHOR_URL is shown.</i>"
    text = f"""{e("link")} <b>Start Buttons</b>
{LINE}
<b>Link buttons:</b>
{rows}

<b>Guide buttons</b> (Leech, Mirror, …): {_onoff(Config.START_GUIDE)}
<b>Source Code button:</b> {_onoff(Config.START_SOURCE_BUTTON)}{note}"""
    b = ButtonMaker()
    for i, k in enumerate(links, 1):
        _btn(b, uid, "remove", f"Remove {i}. {str(k)[:20]}", "link_rm", i - 1)
    _btn(b, uid, "add", "Add Link Button", "link_add", position="f_body")
    _btn(b, uid, "list", f"Guide: {'ON' if Config.START_GUIDE else 'OFF'}", "tog_guide", position="f_body")
    _btn(b, uid, "folder", f"Source: {'ON' if Config.START_SOURCE_BUTTON else 'OFF'}", "tog_src", position="f_body")
    _back(b, uid)
    return text, b.build_menu(1)


async def _bc_page(uid, note=""):
    text = f"""{e("mail")} <b>Broadcast</b>
{LINE}
Send any message (text, photo, video, file, with buttons or premium emoji) to everyone who started the bot.

1. Tap <b>New Broadcast</b>
2. Send the message to me in private chat
3. Check the preview and confirm{note}"""
    b = ButtonMaker()
    _btn(b, uid, "mail", "New Broadcast", "bc_new")
    _back(b, uid)
    return text, b.build_menu(1)


async def _prem_page(uid, note=""):
    text = f"""{e("gem")} <b>Premium Emoji</b>
{LINE}
Animated premium emoji in /start, the guide and this panel.
Telegram only shows them if <b>the bot owner's account has Telegram Premium</b>.
Turning it on sends you a test message first; if Telegram rejects it, it stays off.

<b>Status:</b> {_onoff(Config.PREMIUM_EMOJI)}{note}"""
    b = ButtonMaker()
    _btn(b, uid, "on" if not Config.PREMIUM_EMOJI else "off", "Turn OFF" if Config.PREMIUM_EMOJI else "Turn ON (test)", "prem_tog")
    _back(b, uid)
    return text, b.build_menu(1)


async def _fj_page(uid, note=""):
    chats = fsub_chats()
    rows = "\n".join(
        f"{i}. <b>{escape(c['name'] or '(chat title)')}</b> — <code>{escape(c['id'])}</code>\n    {escape(c['link'] or '(auto link)')}"
        for i, c in enumerate(chats, 1)
    ) or "<i>None — everyone can use the bot.</i>"
    text = f"""{e("key")} <b>Force Join</b>
{LINE}
Users must join these before they can use any command. Owner and sudo are never blocked.
{e("warn")} Make the bot an <b>admin</b> in each channel (a member is enough in groups), otherwise it cannot check members and will not block anyone.

<b>Chats:</b>
{rows}{note}"""
    b = ButtonMaker()
    for i, c in enumerate(chats, 1):
        _btn(b, uid, "remove", f"Remove {i}. {(c['name'] or c['id'])[:20]}", "fj_rm", i - 1)
    _btn(b, uid, "add", "Add Channel / Group", "fj_add", position="f_body")
    _back(b, uid)
    return text, b.build_menu(1)


PAGES = {
    "home": lambda uid, note="": _home(uid),
    "text": _text_page,
    "img": _img_page,
    "btns": _btns_page,
    "bc": _bc_page,
    "fj": _fj_page,
    "prem": _prem_page,
}


async def _show(message, uid, page, note=""):
    text, markup = await PAGES[page](uid, note)
    await edit_message(message, text, markup)


def _note(ok, msg):
    return f"\n\n{e('done') if ok else e('warn')} <i>{msg}</i>"


# ---------- handlers ----------


@new_task
async def admin_panel(_, message):
    uid = message.from_user.id
    text, markup = await _home(uid)
    await send_message(message, text, markup)


@new_task
async def admin_panel_cb(_, query):
    data = query.data.split()
    uid, action = int(data[1]), data[2]
    arg = data[3] if len(data) > 3 else ""
    msg = query.message
    if query.from_user.id != uid:
        await query.answer("This panel belongs to another admin. Send /admin.", show_alert=True)
        return
    if action in PAGES:
        await query.answer()
        return await _show(msg, uid, action)
    if action == "close":
        await query.answer()
        pending_broadcast.pop(uid, None)
        return await delete_message(msg)
    if action == "settings":
        return await query.answer("Send /bsetting for every config variable.", show_alert=True)
    if action == "preview":
        await query.answer("Preview sent to your private chat.")
        text, markup = start_home(query.from_user)
        sent = await send_message(uid, text, markup, photo=start_photo())
        if isinstance(sent, str):
            await TgClient.bot.send_message(uid, f"Preview failed: {escape(sent)}")
        return

    await query.answer()
    # welcome text
    if action == "text_set":
        await edit_message(msg, f"{e('edit')} <i>Waiting for the new welcome text in private chat…</i>")
        reply, err = await _ask(uid, "Send the new welcome text (formatting and premium emoji are kept).")
        if not reply:
            return await _show(msg, uid, "text", _note(False, err) if err else "")
        new_text = getattr(reply, "html", None) or str(reply)
        # greeting + text must fit a photo caption (1024) even with premium emoji tags
        if len(new_text) > 800:
            return await _show(msg, uid, "text", _note(False, "Too long: keep it under 800 characters (photo captions are limited)."))
        test = await send_message(uid, new_text)
        if isinstance(test, str):
            return await _show(msg, uid, "text", _note(False, f"Telegram rejected it: {escape(test)}"))
        await _save("START_TEXT", new_text)
        return await _show(msg, uid, "text", _note(True, "Saved. Above is how it looks."))
    if action == "text_reset":
        await _save("START_TEXT", "")
        return await _show(msg, uid, "text", _note(True, "Back to the built-in text."))
    # welcome image
    if action == "img_set":
        await edit_message(msg, f"{e('image')} <i>Send the photo (or an image URL) to me in private chat…</i>")
        sent = await send_message(uid, f"{e('image')} Send the welcome photo or an image URL within 2 minutes.")
        if isinstance(sent, str):
            return await _show(msg, uid, "img", _note(False, "Start the bot in private chat first, then try again."))
        reply = await _wait_pm(uid)
        if reply is None:
            return await _show(msg, uid, "img", _note(False, "Timed out."))
        if reply.photo:
            photo = reply.photo.file_id
        elif reply.text and valid_url(reply.text.strip()):
            photo = reply.text.strip()
        else:
            return await _show(msg, uid, "img", _note(False, "That is not a photo or an image URL."))
        test = await send_message(uid, f"{e('done')} Welcome image preview", photo=photo)
        if isinstance(test, str) or not getattr(test, "photo", None):
            return await _show(msg, uid, "img", _note(False, "Telegram could not use that image."))
        await _save("START_IMAGE", photo)
        return await _show(msg, uid, "img", _note(True, "Saved."))
    if action == "img_reset":
        await _save("START_IMAGE", "")
        return await _show(msg, uid, "img", _note(True, "Custom image removed."))
    # start buttons
    if action == "link_add":
        await edit_message(msg, f"{e('add')} <i>Waiting for the button in private chat…</i>")
        name, err = await _ask(uid, "Send the button text, e.g. 📢 Updates")
        if not name:
            return await _show(msg, uid, "btns", _note(False, err) if err else "")
        url, err = await _ask(uid, f"Now send the link for <b>{escape(str(name))}</b> (https://… or t.me/…)")
        url = str(url or "").strip()
        if url.startswith("t.me/"):
            url = f"https://{url}"
        if not valid_url(url):
            return await _show(msg, uid, "btns", _note(False, err or "That link is not valid."))
        links = dict(Config.START_LINKS) if isinstance(Config.START_LINKS, dict) else {}
        links[str(name).strip()[:40]] = url
        await _save("START_LINKS", links)
        return await _show(msg, uid, "btns", _note(True, "Button added."))
    if action == "link_rm":
        links = dict(Config.START_LINKS) if isinstance(Config.START_LINKS, dict) else {}
        keys = list(links)
        if arg.isdigit() and int(arg) < len(keys):
            links.pop(keys[int(arg)])
            await _save("START_LINKS", links)
            return await _show(msg, uid, "btns", _note(True, "Button removed."))
        return await _show(msg, uid, "btns")
    if action == "tog_guide":
        await _save("START_GUIDE", not Config.START_GUIDE)
        return await _show(msg, uid, "btns")
    if action == "tog_src":
        await _save("START_SOURCE_BUTTON", not Config.START_SOURCE_BUTTON)
        return await _show(msg, uid, "btns")
    # force join
    if action == "fj_add":
        await edit_message(msg, f"{e('key')} <i>Waiting for the channel/group in private chat…</i>")
        sent = await send_message(
            uid,
            f"{e('key')} Send the channel/group ID (<code>-100…</code>) or @username, "
            "or forward any message from that channel. Add the bot there as admin first.",
        )
        if isinstance(sent, str):
            return await _show(msg, uid, "fj", _note(False, "Start the bot in private chat first, then try again."))
        reply = await _wait_pm(uid)
        if reply is None:
            return await _show(msg, uid, "fj", _note(False, "Timed out."))
        fwd = getattr(reply, "forward_from_chat", None) or getattr(
            getattr(reply, "forward_origin", None), "chat", None
        )
        target = str(fwd.id) if fwd else (reply.text or "").strip()
        chat = await chat_info(target)
        if chat is None:
            return await _show(msg, uid, "fj", _note(False, "I can't open that chat. Add the bot to it (as admin) and use the -100… ID or @username."))
        warn = ""
        try:
            me = await chat.get_member("me")
            if me.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                warn = " The bot is not an admin there yet — make it admin or it can't check members."
        except Exception:
            warn = " Could not confirm the bot's admin rights there — make it admin."
        name, err = await _ask(uid, f"Send the button name for <b>{escape(chat.title or '')}</b>, or send <code>skip</code> to use the chat title.")
        if err:
            return await _show(msg, uid, "fj", _note(False, err))
        name = "" if not name or str(name).strip().lower() == "skip" else str(name).strip()[:40]
        auto_link = f"https://t.me/{chat.username}" if chat.username else (chat.invite_link or "")
        link, err = await _ask(uid, f"Send the join link (https://t.me/…){f', or <code>skip</code> to use {escape(auto_link)}' if auto_link else ''}.")
        link = str(link or "").strip()
        if link.lower() == "skip" or (not link and auto_link):
            link = auto_link
        if link.startswith("t.me/"):
            link = f"https://{link}"
        if not valid_url(link):
            return await _show(msg, uid, "fj", _note(False, err or "A valid join link is needed (private chats have no automatic link)."))
        chats = [c for c in (Config.FORCE_SUB_CHATS if isinstance(Config.FORCE_SUB_CHATS, list) else []) if isinstance(c, dict) and str(c.get("id")) != str(chat.id)]
        chats.append({"id": str(chat.id), "name": name or chat.title or "Join", "link": link})
        await _save("FORCE_SUB_CHATS", chats)
        return await _show(msg, uid, "fj", _note(not warn, f"Added {escape(chat.title or str(chat.id))}.{warn}"))
    if action == "fj_rm":
        chats = fsub_chats()
        if arg.isdigit() and int(arg) < len(chats):
            gone = chats.pop(int(arg))
            await _save("FORCE_SUB_CHATS", [c for c in chats if c["id"] not in str(Config.FORCE_SUB_IDS or "").split()])
            if gone["id"] in str(Config.FORCE_SUB_IDS or "").split():
                await _save("FORCE_SUB_IDS", " ".join(i for i in str(Config.FORCE_SUB_IDS).split() if i != gone["id"]))
            return await _show(msg, uid, "fj", _note(True, "Removed."))
        return await _show(msg, uid, "fj")
    # broadcast
    if action == "bc_new":
        if not Config.DATABASE_URL:
            return await _show(msg, uid, "bc", _note(False, "Broadcast needs DATABASE_URL."))
        await edit_message(msg, f"{e('mail')} <i>Send the message to broadcast to me in private chat…</i>")
        sent = await send_message(uid, f"{e('mail')} Send the message to broadcast within 2 minutes.")
        if isinstance(sent, str):
            return await _show(msg, uid, "bc", _note(False, "Start the bot in private chat first, then try again."))
        reply = await _wait_pm(uid)
        if reply is None:
            return await _show(msg, uid, "bc", _note(False, "Timed out."))
        pending_broadcast[uid] = reply
        b = ButtonMaker()
        _btn(b, uid, "done", "Send to all", "bc_go", 0)
        _btn(b, uid, "off", "Send silently", "bc_go", 1)
        _btn(b, uid, "close", "Cancel", "bc", position="footer")
        return await edit_message(
            msg,
            f"{e('warn')} <b>Confirm broadcast</b>\n{LINE}\nThe message you just sent will be copied to every user.",
            b.build_menu(2),
        )
    if action == "bc_go":
        rply = pending_broadcast.pop(uid, None)
        if not isinstance(rply, Message):
            return await _show(msg, uid, "bc", _note(False, "Nothing to send, start again."))
        await edit_message(msg, f"{e('mail')} <b>Broadcasting…</b> live stats below.")
        bc_id = await run_broadcast(rply, msg, quietly=arg == "1")
        return await _show(msg, uid, "bc", _note(True, f"Done. Broadcast ID: <code>{bc_id}</code> (use /broadcast {bc_id} -d to delete)."))
    # premium emoji
    if action == "prem_tog":
        if Config.PREMIUM_EMOJI:
            await _save("PREMIUM_EMOJI", False)
            return await _show(msg, uid, "prem", _note(True, "Premium emoji turned off."))
        char, emoji_id = EMOJI["gem"]
        b = ButtonMaker()
        b.data_button("Premium test", _cb(uid, "prem"), icon=emoji_id)
        try:
            test = await TgClient.bot.send_message(
                uid,
                f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji> Premium emoji test',
                reply_markup=b.build_menu(1),
            )
        except Exception as ex:
            return await _show(msg, uid, "prem", _note(False, f"Telegram rejected premium emoji: {escape(str(ex))}"))
        entities = getattr(test, "entities", None) or []
        if not any(getattr(x, "custom_emoji_id", None) for x in entities):
            return await _show(msg, uid, "prem", _note(False, "Telegram showed a normal emoji, so premium emoji is not available for this bot (the owner needs Telegram Premium)."))
        await _save("PREMIUM_EMOJI", True)
        return await _show(msg, uid, "prem", _note(True, "Premium emoji is on."))
