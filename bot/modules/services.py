from html import escape
from pyrogram.enums import ButtonStyle, ChatMemberStatus, ChatType
from time import monotonic, time
from uuid import uuid4
from re import match

from aiofiles import open as aiopen
from cloudscraper import create_scraper
from pyrogram.types import BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup

from .. import LOGGER, sudo_users, user_data
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import new_task, update_user_ldata
from ..helper.ext_utils.links_utils import decode_slink
from ..helper.ext_utils.status_utils import get_readable_time
from ..helper.ext_utils.db_handler import database
from ..helper.languages import Language
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.emoji import e, icon, label
from ..helper.telegram_helper.force_join import (
    forget_user,
    fsub_chats,
    join_markup,
    join_text,
    missing_chats,
    pending_prompts,
)
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    edit_reply_markup,
    send_file,
    send_message,
)


GUIDE_BUTTONS = (
    ("download", "Leech", "leech"),
    ("upload", "Mirror", "mirror"),
    ("play", "YouTube & Sites", "yt"),
    ("satellite", "Torrents", "torrent"),
    ("gear", "Settings & Tasks", "settings"),
    ("list", "All Commands", "cmds"),
)


def _cmd(name):
    cmds = getattr(BotCommands, f"{name}Command")
    return f"/{cmds[0] if isinstance(cmds, list) else cmds}"


def _greeting(user):
    return (
        f'{e("wave")} <b>Hey <a href="tg://user?id={user.id}">{escape(user.first_name or "there")}</a></b>\n'
        f'{e("key")} <b>ID:</b> <tg-spoiler><code>{user.id}</code></tg-spoiler>\n\n'
    )


def start_body(lang=None):
    if Config.START_TEXT:
        return Config.START_TEXT
    lang = lang or Language()
    return lang.START_MSG.format(
        cmd=BotCommands.HelpCommand[0],
        leech=BotCommands.LeechCommand[0],
        mirror=BotCommands.MirrorCommand[0],
        ytdl=BotCommands.YtdlCommand[0],
        bolt=e("bolt"),
        dl=e("download"),
        ul=e("upload"),
        play=e("play"),
        cmds=e("list"),
    )


def start_photo():
    return Config.START_IMAGE or "IMAGES"


def _start_links(buttons, lang):
    links = Config.START_LINKS if isinstance(Config.START_LINKS, dict) else {}
    for label_, url in links.items():
        buttons.url_button(str(label_), str(url), "f_body", ButtonStyle.SUCCESS)
    if not links:
        # no custom links: show the force join chats (channel + bot group)
        for chat in fsub_chats():
            if chat["name"] and chat["link"]:
                buttons.url_button(chat["name"], chat["link"], "f_body", ButtonStyle.SUCCESS)


def view_only(user_id, chat):
    """Private chat with someone who may only use the bot inside the allowed groups."""
    if chat is None or chat.type != ChatType.PRIVATE:
        return False
    data = user_data.get(user_id, {})
    return not (
        user_id == Config.OWNER_ID
        or user_id in sudo_users
        or data.get("AUTH")
        or data.get("SUDO")
    )


def is_admin(user_id):
    return (
        user_id == Config.OWNER_ID
        or user_id in sudo_users
        or bool(user_data.get(user_id, {}).get("SUDO"))
    )


def start_home(user, view=False, admin=None):
    """admin=None: owner/sudo get the red Admin Panel button in place of the links."""
    lang = Language()
    buttons = ButtonMaker()
    if Config.START_GUIDE:
        for name, text, page in GUIDE_BUTTONS:
            buttons.data_button(
                label(name, text), f"guide {user.id} {page}", icon=icon(name)
            )
    if is_admin(user.id) if admin is None else admin:
        buttons.data_button(
            label("gem", "Admin Panel"),
            f"adm {user.id} home",
            "f_body",
            style=ButtonStyle.DANGER,
            icon=icon("gem"),
        )
    else:
        _start_links(buttons, lang)
    text = _greeting(user) + start_body(lang)
    if view:
        text += (
            f"\n{e('chat')} <b>Downloads work only in our bot group</b> — "
            "open it with the button below and send your commands there."
        )
        if Config.BOT_PM:
            text += "\n<i>Your files will also be sent to you here.</i>"
    return text, buttons.build_menu(2)


def _guide_text(page):
    # kept short: on a photo message this is a caption (1024 chars max)
    leech, mirror = _cmd("Leech"), _cmd("Mirror")
    pages = {
        "leech": f"""{e("download")} <b>Leech — get files in Telegram</b>

Send <code>{leech} link</code> or reply to a link/file with {leech}.

<b>Handy options</b>
<blockquote expandable>├ <code>-n new name</code> → rename
├ <code>-z</code> → zip  •  <code>-e</code> → unzip
├ <code>-doc</code> / <code>-med</code> → send as file / media
└ <code>-sp 2GB</code> → split size</blockquote>

<b>Example</b>
<code>{leech} https://site.com/file.zip -e</code>""",
        "mirror": f"""{e("upload")} <b>Mirror — save files to your cloud</b>

Send <code>{mirror} link</code> or reply with {mirror}.
Files go to Google Drive or rclone (set your own in {_cmd("UserSet")}).

<b>Handy options</b>
<blockquote expandable>├ <code>-up rcl</code> → pick an rclone folder
├ <code>-up gdl</code> → pick a Drive folder
├ <code>-z</code> → zip  •  <code>-e</code> → unzip
└ <code>-n new name</code> → rename</blockquote>

{e("folder")} Manage cloud files with {_cmd("RcloneFm")}.""",
        "yt": f"""{e("play")} <b>YouTube &amp; 1000+ sites</b>

<b>Video/audio</b>
├ {_cmd("YtdlLeech")} <code>link</code> → to Telegram
└ {_cmd("Ytdl")} <code>link</code> → to cloud
A quality menu appears after you send it.

{e("image")} <b>Images/galleries</b> (Instagram, Pixiv, Reddit…)
├ {_cmd("GallerydlLeech")} <code>link</code>
└ {_cmd("Gallerydl")} <code>link</code>

{e("key")} Private videos need cookies: {_cmd("UserSet")} → YT-DLP.""",
        "torrent": f"""{e("satellite")} <b>Torrents &amp; magnets</b>

Send a magnet link or reply to a .torrent with:
├ {leech} → to Telegram
├ {_cmd("QbLeech")} → qBittorrent (choose files)
└ {mirror} / {_cmd("QbMirror")} → to cloud

<b>Handy options</b>
<blockquote expandable>├ <code>-s</code> → select files before download
├ <code>-ad</code> / <code>-tb</code> → AllDebrid / TorBox (faster)
└ {e("search")} {_cmd("Search")} <code>name</code> → search torrents</blockquote>""",
        "settings": f"""{e("gear")} <b>Settings &amp; tasks</b>

{_cmd("UserSet")} → your own settings: thumbnail, caption,
leech type, rclone config, cookies, upload paths.

{e("chart")} <b>While a task runs</b>
├ {_cmd("Status")} → progress of all tasks
├ {_cmd("CancelTask")} <code>gid</code> → stop one task
└ {_cmd("CancelAll")} → stop all your tasks

{e("server")} {_cmd("Stats")} → bot and server info.""",
        "cmds": f"""{e("list")} <b>All commands</b>

Send {_cmd("Help")} for the full list with every option.
Type <b>/</b> in the chat to see the command menu.""",
    }
    return pages.get(page, pages["cmds"])


@new_task
async def force_join_gate(_, message):
    uid = (message.from_user or message.sender_chat).id
    if missing := await missing_chats(uid):
        sent = await send_message(message, join_text(missing), join_markup(uid, missing))
        if not isinstance(sent, str):
            pending_prompts[uid] = sent


@new_task
async def force_join_cb(_, query):
    uid = int(query.data.split()[1])
    if uid != query.from_user.id:
        await query.answer("Send /start yourself to use this menu.", show_alert=True)
        return
    if missing := await missing_chats(uid, use_cache=False):
        names = ", ".join(name for name, _ in missing)
        await query.answer(f"Not joined yet: {names}"[:190], show_alert=True)
        return
    await query.answer("Thanks for joining!")
    pending_prompts.pop(uid, None)
    text, markup = start_home(query.from_user, view_only(uid, query.message.chat))
    await edit_message(query.message, text, markup)


JOINED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.OWNER,
    ChatMemberStatus.RESTRICTED,
}


@new_task
async def force_join_member_update(_, update):
    # auto verify: Telegram sends these for chats where the bot is admin
    new = update.new_chat_member
    if not new or not new.user or new.status not in JOINED_STATUSES:
        return
    if str(update.chat.id) not in {c["id"] for c in fsub_chats()}:
        return
    uid = new.user.id
    forget_user(uid)
    if (prompt := pending_prompts.get(uid)) is None:
        return
    if missing := await missing_chats(uid, use_cache=False):
        await edit_message(prompt, join_text(missing), join_markup(uid, missing))
        return
    pending_prompts.pop(uid, None)
    text, markup = start_home(new.user, view_only(uid, getattr(prompt, "chat", None)))
    await edit_message(prompt, text, markup)


@new_task
async def guide_cb(_, query):
    _, uid, page = query.data.split()
    if int(uid) != query.from_user.id:
        await query.answer("Send /start yourself to use this menu.", show_alert=True)
        return
    await query.answer()
    if page == "home":
        text, markup = start_home(query.from_user, view_only(int(uid), query.message.chat))
    else:
        buttons = ButtonMaker()
        buttons.data_button(label("back", "Home"), f"guide {uid} home", icon=icon("back"))
        text, markup = _guide_text(page), buttons.build_menu(1)
    await edit_message(query.message, text, markup)


async def ensure_admin_menu(user_id):
    """Set the full command menu in an owner/sudo chat once the bot knows the chat."""
    if user_id in BotCommands.admin_menu_set or not BotCommands.ADMIN_MENU:
        return
    try:
        await TgClient.bot.set_bot_commands(
            BotCommands.ADMIN_MENU, scope=BotCommandScopeChat(user_id)
        )
        BotCommands.admin_menu_set.add(user_id)
    except Exception as err:
        LOGGER.warning(f"Admin command menu not set for {user_id}: {err}")


@new_task
async def start(_, message):
    userid = message.from_user.id
    if await CustomFilters.sudo(_, message):
        await ensure_admin_menu(userid)
    lang = Language()
    buttons = ButtonMaker()
    _start_links(buttons, lang)
    reply_markup = buttons.build_menu(2)
    greeting = _greeting(message.from_user)

    if len(message.command) > 1 and message.command[1] == "wzmlx":
        await delete_message(message)
    elif len(message.command) > 1 and message.command[1] != "start":
        decrypted_url = decode_slink(message.command[1])
        if Config.MEDIA_STORE and decrypted_url.startswith("file"):
            decrypted_url = decrypted_url.replace("file", "")
            chat_id, msg_id = decrypted_url.split("&&")
            LOGGER.info(f"Copying message from {chat_id} & {msg_id} to {userid}")
            return await TgClient.bot.copy_message(  # TODO: make it function
                chat_id=userid,
                from_chat_id=int(chat_id) if match(r"\d+", chat_id) else chat_id,
                message_id=int(msg_id),
                disable_notification=True,
            )
        elif Config.VERIFY_TIMEOUT:
            input_token, pre_uid = decrypted_url.split("&&")
            if int(pre_uid) != userid:
                return await send_message(
                    message,
                    "<b>Access Token is not yours!</b>\n\n<i>Kindly generate your own to use.</i>",
                )
            data = user_data.get(userid, {})
            if "VERIFY_TOKEN" not in data or data["VERIFY_TOKEN"] != input_token:
                return await send_message(
                    message,
                    "<b>Access Token already used!</b>\n\n<i>Kindly generate a new one.</i>",
                )
            elif (
                Config.LOGIN_PASS
                and data["VERIFY_TOKEN"].casefold() == Config.LOGIN_PASS.casefold()
            ):
                return await send_message(
                    message,
                    "<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>",
                )
            buttons.data_button(
                "Activate Access Token", f"start pass {input_token}", "header"
            )
            reply_markup = buttons.build_menu(2)
            msg = f"""{e('key')} <b>Access Login Token</b>
<blockquote><b>Status</b> → <code>Generated Successfully</code>
<b>Access Token</b> → <code>{input_token}</code>

<b>Validity:</b> {get_readable_time(int(Config.VERIFY_TIMEOUT))}</blockquote>"""
            return await send_message(message, msg, reply_markup)

    if await CustomFilters.authorized(_, message):
        text, markup = start_home(message.from_user)
        await send_message(message, text, markup, photo=start_photo())
    elif message.chat.type == ChatType.PRIVATE:
        # group members: join first, then they can view everything here and use it in the group
        if missing := await missing_chats(userid):
            sent = await send_message(message, join_text(missing), join_markup(userid, missing))
            if not isinstance(sent, str):
                pending_prompts[userid] = sent
        else:
            text, markup = start_home(message.from_user, view=True)
            await send_message(message, text, markup, photo=start_photo())
    else:
        await send_message(
            message,
            f"{greeting}{e('bolt')} <b>Mirror Leech Villan Bot</b>\n"
            "<i>Mirror &amp; leech links, Telegram files, torrents, NZB and cloud drives "
            "to Telegram, Google Drive or any rclone cloud.</i>\n\n"
            f"{e('blocked')} <b>You are not authorized yet.</b>\n"
            f"Send your ID <code>{userid}</code> to the bot owner to get access.",
            reply_markup,
            photo=start_photo(),
        )
    await database.set_pm_users(userid)


@new_task
async def start_cb(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[2]
    data = user_data.get(user_id, {})

    if input_token == "activated":
        return await query.answer("Already Activated!", show_alert=True)
    elif "VERIFY_TOKEN" not in data or data["VERIFY_TOKEN"] != input_token:
        return await query.answer("Already Used, Generate New One", show_alert=True)

    update_user_ldata(user_id, "VERIFY_TOKEN", str(uuid4()))
    update_user_ldata(user_id, "VERIFY_TIME", time())
    if Config.DATABASE_URL:
        await database.update_user_data(user_id)
    await query.answer("Activated Access Login Token!", show_alert=True)

    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(
        0,
        [InlineKeyboardButton("✅️ Activated ✅", callback_data="start pass activated")],
    )
    await edit_reply_markup(query.message, InlineKeyboardMarkup(kb))


@new_task
async def login(_, message):
    if Config.LOGIN_PASS is None:
        return await send_message(message, "<i>Login is not enabled !</i>")
    elif len(message.command) > 1:
        user_id = message.from_user.id
        input_pass = message.command[1]

        if user_data.get(user_id, {}).get("VERIFY_TOKEN", "") == Config.LOGIN_PASS:
            return await send_message(
                message, "<b>Already Bot Login In!</b>\n\n<i>No Need to Login Again</i>"
            )

        if input_pass.casefold() != Config.LOGIN_PASS.casefold():
            return await send_message(
                message, "<b>Wrong Password!</b>\n\n<i>Kindly check and try again</i>"
            )

        update_user_ldata(user_id, "VERIFY_TOKEN", Config.LOGIN_PASS)
        if Config.DATABASE_URL:
            await database.update_user_data(user_id)
        return await send_message(
            message, "<b>Bot Permanent Logged In!</b>\n\n<i>Now you can use the bot</i>"
        )
    else:
        await send_message(
            message, "<b>Bot Login Usage :</b>\n\n<code>/login [password]</code>"
        )


@new_task
async def ping(_, message):
    start_time = monotonic()
    reply = await send_message(message, "<i>Starting Ping..</i>")
    end_time = monotonic()
    await edit_message(
        reply, f"<i>Pong!</i>\n <code>{int((end_time - start_time) * 1000)} ms</code>"
    )


@new_task
async def log(_, message):
    uid = message.from_user.id
    buttons = ButtonMaker()
    buttons.data_button("Log Disp", f"log {uid} disp")
    buttons.data_button("Web Log", f"log {uid} web")
    buttons.data_button("Close", f"log {uid} close", style=ButtonStyle.DANGER)
    await send_file(message, "log.txt", buttons=buttons.build_menu(2))


@new_task
async def log_cb(_, query):
    data = query.data.split()
    message = query.message
    user_id = query.from_user.id
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "close":
        await query.answer()
        await delete_message(message, message.reply_to_message)
    elif data[2] == "disp":
        await query.answer("Fetching Log..")
        async with aiopen("log.txt", "r") as f:
            content = await f.read()

        def parse(line):
            parts = line.split("] [", 1)
            return f"[{parts[1]}" if len(parts) > 1 else line

        try:
            res, total = [], 0
            for line in reversed(content.splitlines()):
                line = parse(line)
                res.append(line)
                total += len(line) + 1
                if total > 3500:
                    break

            text = f"<b>Showing Last {len(res)} Lines from log.txt:</b> \n\n----------<b>START LOG</b>----------\n\n<blockquote expandable>{escape('\n'.join(reversed(res)))}</blockquote>\n----------<b>END LOG</b>----------"

            btn = ButtonMaker()
            btn.data_button("Close", f"log {user_id} close", style=ButtonStyle.DANGER)
            await send_message(message, text, btn.build_menu(1))
            await edit_reply_markup(message, None)
        except Exception as err:
            LOGGER.error(f"TG Log Display : {str(err)}")
    elif data[2] == "web":
        boundary = "R1eFDeaC554BUkLF"
        headers = {
            "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
            "Origin": "https://spaceb.in",
            "Referer": "https://spaceb.in/",
            "sec-ch-ua": '"Not-A.Brand";v="99", "Chromium";v="124"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        }

        async with aiopen("log.txt", "r") as f:
            content = await f.read()

        data = (
            f"------WebKitFormBoundary{boundary}\r\n"
            f'Content-Disposition: form-data; name="content"\r\n\r\n'
            f"{content}\r\n"
            f"------WebKitFormBoundary{boundary}--\r\n"
        )

        cget = create_scraper().request
        resp = cget("POST", "https://spaceb.in/", headers=headers, data=data)
        if resp.status_code == 200:
            await query.answer("Generating..")
            btn = ButtonMaker()
            btn.url_button("📨 Web Paste (SB)", resp.url, style=ButtonStyle.PRIMARY)
            await edit_reply_markup(message, btn.build_menu(1))
        else:
            await query.answer("Web Paste Failed ! Check Logs", show_alert=True)
