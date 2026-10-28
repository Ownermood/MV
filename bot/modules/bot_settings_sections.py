# Bot Settings layout: config variables grouped into sections, search and page
# numbers. Only the navigation lives here; editing still goes through
# "botset editvar KEY" in bot_settings.py, so every variable keeps its handler.
from html import escape

from pyrogram.enums import ButtonStyle

from ..core.config_manager import Config
from ..helper.telegram_helper.emoji import e
from .bot_settings_vars import BOOL_VARS, DEFAULT_DESP, LIMIT_VARS

PER_PAGE = 8

_UPPER = {
    "PM", "ID", "URL", "API", "GD", "YT", "DL", "RSS", "NZB", "JD", "TG", "SA", "FF",
    "IP", "TTL", "UI", "TMDB", "IMDB", "CPU", "RC", "SSL", "UL", "DDL", "TV",
}
_WORDS = {"DESP": "Description", "IMG": "Image", "CMDS": "Commands", "CMD": "Command",
          "INC": "Incomplete", "PASS": "Password", "MEM": "Memory", "DIR": "Folder"}


def pretty_key(key):
    """LEECH_SPLIT_SIZE -> Leech Split Size (the real name stays in callbacks)."""
    words = []
    for w in key.split("_"):
        if not w:
            continue
        words.append(w if w in _UPPER else _WORDS.get(w, w.capitalize()))
    return " ".join(words)

# id: (emoji name, title, what the map says, keys). "adv" takes every key not listed.
SECTIONS = {
    "bot": ("users", "Bot", "owner, sudo, auth, start, images", [
        "OWNER_ID", "SUDO_USERS", "AUTHORIZED_CHATS", "BOT_TOKEN", "TELEGRAM_API",
        "TELEGRAM_HASH", "DATABASE_URL", "CMD_SUFFIX", "DEFAULT_LANG", "TIMEZONE",
        "SET_COMMANDS", "AUTHOR_NAME", "AUTHOR_URL", "START_LINKS", "START_TEXT",
        "START_IMAGE", "START_GUIDE", "PREMIUM_EMOJI", "RICH_STATUS", "IMAGES", "USE_IMAGES",
        "IMG_SEARCH", "IMG_PAGE", "IMG_SOURCES", "STATUS_UPDATE_INTERVAL",
        "DELETE_LINKS", "INC_TASK_NOTIFY", "INC_TASK_RESUME", "UPSTREAM_REPO",
        "UPSTREAM_BRANCH",
    ]),
    "leech": ("download", "Leech", "split, PM, dump, caption, thumbnail", [
        "LEECH_SPLIT_SIZE", "LEECH_SECTIONS", "EQUAL_SPLITS", "MEDIA_GROUP", "BOT_PM", "AS_DOCUMENT",
        "LEECH_DUMP_CHATS", "LEECH_PREFIX", "LEECH_SUFFIX", "LEECH_CAPTION",
        "LEECH_FONT", "THUMBNAIL_LAYOUT", "AUTO_THUMBNAIL", "NAME_SWAP",
        "EXCLUDED_EXTENSIONS", "MEDIA_STORE", "TRANSMISSION_MODE",
        "USER_SESSION_STRING", "USER_SESSION_KEY_TTL", "USER_SESSION_IDLE",
        "USER_SESSION_MAX_CLIENTS", "HELPER_TOKENS", "HELPER_STRINGS",
        "HELPER_BOT_PROXIES", "HELPER_USER_PROXIES",
    ]),
    "cloud": ("upload", "Cloud", "GDrive, rclone, clone, hosters, YouTube", [
        "DEFAULT_UPLOAD", "GDRIVE_ID", "IS_TEAM_DRIVE", "INDEX_URL",
        "USE_SERVICE_ACCOUNTS", "GD_DESP", "DRIVE_CATEGORY_MODE", "DRIVE_CATEGORY_SA",
        "UPLOAD_PATHS", "RCLONE_PATH", "RCLONE_FLAGS", "RCLONE_SERVE_URL",
        "RCLONE_SERVE_USER", "RCLONE_SERVE_PASS", "RCLONE_SERVE_PORT",
        "SHOW_CLOUD_LINK", "CLONE_CONTENT_TYPE", "CLONE_DUMP_CHATS",
        "CLONE_EXCLUDED_EXTENSIONS", "CLONE_FILTERS", "GOFILE_API", "GOFILE_FOLDER_ID",
        "GOFILE_AUTO_CREATE_FOLDER", "PIXELDRAIN_KEY", "BUZZHEAVIER_API",
        "DEVUPLOADS_KEY", "DEVUPLOADS_FOLDER", "VIKINGFILE_HASH", "VIKINGFILE_FOLDER",
        "FILELION_API", "STREAMWISH_API", "PROTECTED_API", "YT_DESP", "YT_TAGS",
        "YT_CATEGORY_ID", "YT_PRIVACY_STATUS",
    ]),
    "dl": ("link", "Downloaders", "yt-dlp, gallery-dl, debrid, Mega, Seedr", [
        "YT_DLP_OPTIONS", "GALLERY_DL_OPTIONS", "FFMPEG_CMDS", "TORBOX_API_KEY",
        "ALLDEBRID_API_KEY", "ALLDEBRID_NO_SEED_TIMEOUT", "DEBRID_LINK_API",
        "TLDV_TOKEN", "INSTADL_API", "MEGA_EMAIL", "MEGA_PASSWORD", "SEEDR_EMAIL",
        "SEEDR_PASSWORD", "SEEDR_DELETE_FOLDER", "JD_EMAIL", "JD_PASS",
        "TMDB_ACCESS_TOKEN", "IMDB_TEMPLATE",
    ]),
    "torrent": ("satellite", "Torrent/NZB", "timeout, web UI, search, usenet", [
        "TORRENT_TIMEOUT", "BASE_URL", "WEB_PINCODE", "WEB_ACCESS_PASSWORD",
        "SEARCH_API_LINK", "SEARCH_PLUGINS", "USENET_SERVERS", "HYDRA_IP",
        "HYDRA_API_KEY",
    ]),
    "limits": ("blocked", "Limits", "tasks, queue, size limits, access", [
        "BOT_MAX_TASKS", "USER_MAX_TASKS", "USER_TIME_INTERVAL", "QUEUE_ALL",
        "QUEUE_DOWNLOAD", "QUEUE_UPLOAD", "STOP_DUPLICATE", "VERIFY_TIMEOUT",
        "LOGIN_PASS", "FORCE_SUB_IDS", "FORCE_SUB_CHATS", "CLONE_TG_LIMIT", *LIMIT_VARS,
    ]),
    "logs": ("bell", "Logs", "log chats, RSS", [
        "ERROR_LOG_CHAT", "LEECH_LOG_CHAT", "MIRROR_LOG_ID", "LINKS_LOG_ID", "RSS_CHAT", "RSS_DELAY",
        "ENABLE_TELEMETRY",
    ]),
    "adv": ("gear", "Advanced", "speed, memory, proxy, plugins, rest", []),
}


def editable_keys():
    """Every variable that opens with editvar (DISABLE_* live in Module Settings)."""
    return [k for k in Config.get_all() if not k.startswith("DISABLE_")]


def section_keys(sid):
    keys = editable_keys()
    if sid != "adv":
        listed = SECTIONS[sid][3]
        return [k for k in listed if k in keys]
    listed = {k for _, _, _, ks in SECTIONS.values() for k in ks}
    return [k for k in keys if k not in listed]


def search_keys(query):
    words = query.casefold().replace("_", " ").split()
    found = []
    for k in editable_keys():
        hay = f"{k.replace('_', ' ')} {DEFAULT_DESP.get(k, '')}".casefold()
        if all(w in hay for w in words):
            found.append(k)
    # names that match come first
    return sorted(found, key=lambda k: not all(w in k.casefold().replace("_", " ") for w in words))


def short_desc(key, limit=70):
    text = " ".join(str(DEFAULT_DESP.get(key, "")).split())
    text = text.split(". ")[0].rstrip(".")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def key_state(key):
    """'on', 'off', 'set' or 'empty'. Values are never shown: many are secrets."""
    value = Config.get(key)
    if key in BOOL_VARS or isinstance(value, bool):
        return "on" if value else "off"
    return "set" if value not in ("", None, 0, [], {}) else "empty"


_STATE_TEXT = {
    "on": ("done", "ON"),
    "off": ("off", "OFF"),
    "set": ("key", "Set"),
    "empty": ("remove", "Empty"),
}


def key_list_text(keys):
    rows = []
    for k in keys:
        icon_name, word = _STATE_TEXT[key_state(k)]
        desc = short_desc(k)
        rows.append(
            f"{e(icon_name)} <b>{pretty_key(k)}</b> · <i>{word}</i>"
            + (f"\n      {escape(desc)}" if desc else "")
        )
    return "\n\n".join(rows)


def page_buttons(buttons, pages, current, data_fmt):
    """Numbered page buttons 1 2 3 …: open page green, the rest blue."""
    if pages <= 1:
        return
    for n in range(1, pages + 1):
        buttons.data_button(
            f"• {n} •" if n == current else str(n),
            data_fmt.format(n),
            position="l_body",
            style=ButtonStyle.SUCCESS if n == current else ButtonStyle.PRIMARY,
        )


def page_slice(keys, page):
    pages = max(1, -(-len(keys) // PER_PAGE))
    page = min(max(page, 1), pages)
    return keys[(page - 1) * PER_PAGE : page * PER_PAGE], page, pages


def home_text():
    rows = [
        f"{e(icon)} <b>{title}</b> → {about}"
        for icon, title, about, _ in SECTIONS.values()
    ]
    rows += [
        f"{e('on')} <b>Modules</b> → turn features on/off",
        f"{e('key')} <b>Private Files</b> → token.pickle, rclone.conf, cookies",
        f"{e('server')} <b>Engines</b> → qBit, Aria2, SABnzbd options",
        f"{e('search')} <b>Search</b> → find any setting by name or word",
    ]
    return (
        f"{e('gear')} <b>Bot Settings</b>\n"
        "<blockquote expandable>" + "\n".join(rows) + "</blockquote>\n"
        "<i>Open a section: every setting shows what it does and if it is set.</i>"
    )


def section_text(sid, keys, page, pages):
    icon, title, about, _ = SECTIONS[sid]
    return (
        f"{e(icon)} <b>{title} Settings</b>\n"
        f"<i>{about}</i>  ·  page {page}/{pages}\n\n"
        f"<blockquote expandable>{key_list_text(keys) or 'Nothing here.'}</blockquote>\n"
        f"{e('info')} <i>Tap a setting below to view or change it.</i>"
    )


def search_text(query, keys, page, pages, total):
    if not total:
        return (
            f"{e('search')} <b>Search:</b> <code>{escape(query)}</code>\n\n"
            "<i>No setting matches. Try a shorter word, like</i> <code>split</code>, "
            "<code>log</code> <i>or</i> <code>drive</code>."
        )
    return (
        f"{e('search')} <b>Search:</b> <code>{escape(query)}</code> · {total} found · page {page}/{pages}\n\n"
        f"<blockquote expandable>{key_list_text(keys)}</blockquote>\n"
        f"{e('info')} <i>Tap a setting below to view or change it.</i>"
    )
