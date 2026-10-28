from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from pyrogram.enums import ButtonStyle

URL_SCHEMES = ("http://", "https://", "tg://")


def _btn_style(style=None):
    return style or ButtonStyle.DEFAULT


def valid_url(link):
    text = str(link or "").strip()
    if not text.lower().startswith(URL_SCHEMES):
        return ""
    rest = text.split("://", 1)[1]
    if not rest or rest.startswith(("/", "?", "#")):
        return ""
    if any(ch.isspace() for ch in text):
        return ""
    return text


# longest label (in characters) that still shows whole on a phone when a row
# has this many buttons
_ROW_FIT = {1: 10**6, 2: 17, 3: 11, 4: 8, 5: 6}


def _fits(count):
    return _ROW_FIT.get(count, 4)


def _width(btn):
    # a premium icon takes about two characters of room
    return len(btn.text or "") + (2 if btn.icon_custom_emoji_id else 0)


class ButtonMaker:
    def __init__(self):
        self.buttons = {
            "default": [],
            "header": [],
            "f_body": [],
            "l_body": [],
            "footer": [],
        }

    def url_button(self, key, link, position=None, style=None, icon=None):
        safe = valid_url(link)
        if not safe:
            from ... import LOGGER

            LOGGER.warning(f"dropping button {key!r} with unusable url {link!r}")
            return
        self.buttons[position if position in self.buttons else "default"].append(
            InlineKeyboardButton(
                text=key, url=safe, style=_btn_style(style), icon_custom_emoji_id=icon
            )
        )

    def web_app_button(self, key, link, position=None, style=None):
        self.buttons[position if position in self.buttons else "default"].append(
            InlineKeyboardButton(
                text=key, web_app=WebAppInfo(url=link), style=_btn_style(style)
            )
        )

    def data_button(self, key, data, position=None, style=None, icon=None):
        if style is None and str(key).strip().endswith("Back"):
            style = ButtonStyle.DANGER  # every Back button is red
        self.buttons[position if position in self.buttons else "default"].append(
            InlineKeyboardButton(
                text=key,
                callback_data=data,
                style=_btn_style(style),
                icon_custom_emoji_id=icon,
            )
        )

    def build_menu(self, b_cols=1, h_cols=8, fb_cols=2, lb_cols=2, f_cols=8):
        def chunk(lst, n):
            # up to n buttons a row, but a label too long to show whole next
            # to the others gets a row of its own (Telegram cuts it with "…")
            rows, row = [], []
            for btn in lst:
                cand = row + [btn]
                if len(cand) <= n and max(map(_width, cand)) <= _fits(len(cand)):
                    row = cand
                    continue
                if row:
                    rows.append(row)
                row = [btn]
            if row:
                rows.append(row)
            return rows

        menu = chunk(self.buttons["default"], b_cols)
        menu = (
            chunk(self.buttons["header"], h_cols) if self.buttons["header"] else []
        ) + menu
        for key, cols in (("f_body", fb_cols), ("l_body", lb_cols), ("footer", f_cols)):
            if self.buttons[key]:
                menu += chunk(self.buttons[key], cols)
        return InlineKeyboardMarkup(menu)

    def reset(self):
        for key in self.buttons:
            self.buttons[key].clear()
