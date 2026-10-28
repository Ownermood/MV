# Premium (custom) emoji used across the UI. Telegram only shows them when the
# bot owner has Telegram Premium, so they are opt-in via PREMIUM_EMOJI and every
# entry keeps a normal emoji fallback.
from ...core.config_manager import Config

EMOJI = {
    # UI_Icons pack (@technoprint_official)
    "search": ("🔎", "5445023138297447592"),
    "folder": ("📂", "5447282724886839705"),
    "download": ("⬇️", "5444961234933806330"),
    "upload": ("⬆️", "5444988177263654261"),
    "done": ("✅", "5444987348334965906"),
    "add": ("➕", "5447224884562263112"),
    "remove": ("➖", "5447155993286832278"),
    "play": ("▶️", "5444883062234053429"),
    "chat": ("💬", "5445140257760639304"),
    "blocked": ("🚫", "5447647474984449520"),
    "bolt": ("⚡️", "5445388803223091254"),
    "warn": ("⚠️", "5447381715293074599"),
    "image": ("🖼", "5447588260270341594"),
    "edit": ("📝", "5444889156792646660"),
    "trash": ("🗑", "5445005936953424165"),
    "on": ("🔛", "5445279663809130789"),
    "off": ("📴", "5445349654596189741"),
    "users": ("🫂", "5445372439397691719"),
    # the pack's "❌" (5445092669522996408) is drawn as a person icon; the
    # second 🚫 of the pack is used for close/cancel/stop instead
    "close": ("❌", "5447385112612208213"),
    "link": ("🔗", "5447479640547428304"),
    "back": ("↩️", "5445362436418859744"),
    "prev": ("⬅️", "5447506720316225765"),
    "next": ("➡️", "5445350109862720603"),
    "gear": ("⚙️", "5444869180899752137"),
    "server": ("🖥", "5447607759421863856"),
    "list": ("📋", "5445260044398524944"),
    "bell": ("🔔", "5445333299360723379"),
    "chart": ("📊", "5445146408153806223"),
    "mail": ("📬", "5445163772706582819"),
    "key": ("🔑", "5445373775132522312"),
    "info": ("ℹ️", "5247236071795754971"),
    "gem": ("💎", "5260681660189408650"),
    "star": ("⭐️", "5444939047132755535"),
    "clock": ("⏰", "5445350406215465190"),
    "satellite": ("📡", "5447448489149625830"),
    "globe": ("🌐", "5447602197439218445"),
    "video": ("📹", "5445344161333015312"),
    "exit": ("🚪", "5447434637880098257"),
    # Peach and Goma pack (@TgEmojis)
    "wave": ("👋", "5424611538151437896"),
    "love": ("🥰", "5422868133616557832"),
    "party": ("🥳", "5424968454228680999"),
    "laptop": ("💻", "5424994438780821530"),
    "question": ("❓", "5424700761802023186"),
}


def e(name):
    """Emoji for message text: premium when enabled, plain otherwise."""
    char, emoji_id = EMOJI[name]
    if Config.PREMIUM_EMOJI and emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{char}</tg-emoji>'
    return char


def icon(name):
    """custom_emoji_id for a button icon, or None when premium emoji is off."""
    return (EMOJI[name][1] or None) if Config.PREMIUM_EMOJI and name in EMOJI else None


def label(name, text):
    """Button text: the premium icon replaces the leading emoji when enabled."""
    return text if icon(name) else f"{EMOJI[name][0]} {text}"
