# Rich message version of the status card (Telegram rich messages): the same
# lines as the HTML card plus dividers and coloured buttons inside the text. Built from the same
# data as the HTML card; callers fall back to HTML when sending this fails.
from pyrogram import raw
from pyrogram.types import (
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichMessage,
)

from ...core.config_manager import Config
from ..telegram_helper.emoji import EMOJI


def _plain(text):
    return raw.types.TextPlain(text=str(text))


def _concat(*parts):
    return raw.types.TextConcat(texts=[p for p in parts if p is not None])


def _bold(text):
    return raw.types.TextBold(text=_plain(text))


def _emoji(name):
    char, emoji_id = EMOJI[name]
    if Config.PREMIUM_EMOJI:
        return raw.types.TextCustomEmoji(document_id=int(emoji_id), alt=char)
    return _plain(char)


def _button(icon_name, text, data, style):
    return raw.types.TextButton(
        text=_concat(_emoji(icon_name), _plain(f" {text}")),
        type=raw.types.InlineButtonTypeCallback(data=data.encode()),
        style=raw.types.RichButtonStyle(**{f"bg_{style}": True}),
    )


def _lines(parts):
    """Join lists of rich text pieces with line breaks in one paragraph."""
    out = []
    for i, line in enumerate(parts):
        if i:
            out.append(_plain("\n"))
        out.extend(line)
    return _concat(*out)


def build_rich_status(header, tasks, stats, nav):
    """header: text; tasks: dicts from get_readable_message; stats: two lines of
    (key, value) pairs; nav: (icon, text, callback data) buttons under the card."""
    blocks = [
        InputRichBlockParagraph(
            _concat(_emoji("list"), _plain(" "), raw.types.TextMarked(text=_bold(header)))
        )
    ]
    for task in tasks:
        blocks.append(InputRichBlockDivider())
        lines = [
            [_emoji(task["icon"]), _plain(" "), _bold(task["title"])],
            [raw.types.TextItalic(text=_plain(task["name"]))],
        ]
        if task["sub"]:
            lines.append([raw.types.TextItalic(text=_plain(f"↳ {task['sub']}"))])
        if task["bar"]:
            lines.append([_plain(f"{task['bar']} "), _bold(task["pct"])])
        lines += [[_bold(f"{k}: "), _plain(v)] for k, v in task["fields"]]
        user_name, user_id = task["user"]
        lines.append(
            [
                _bold("User: "),
                raw.types.TextUrl(
                    text=_plain(user_name), url=f"tg://user?id={user_id}", webpage_id=0
                ),
                _plain(f" ({user_id})"),
            ]
        )
        blocks.append(InputRichBlockParagraph(_lines(lines)))
        actions = [_button("close", "Cancel Task", f"rcan {task['gid']}", "danger")]
        if task["select"]:
            actions += [
                _plain("  "),
                _button("folder", "Select Files", f"rsel {task['gid']}", "primary"),
            ]
        blocks.append(InputRichBlockParagraph(_concat(*actions)))
    blocks.append(InputRichBlockDivider())
    stat_lines = [[_emoji("chart"), _plain(" "), _bold("Bot Stats")]]
    for row in stats:
        line = []
        for i, (k, v) in enumerate(row):
            if i:
                line.append(_plain(" | "))
            line += [_bold(f"{k}: "), _plain(v)]
        stat_lines.append(line)
    blocks.append(InputRichBlockParagraph(_lines(stat_lines)))
    buttons = []
    for i, (icon_name, text, data) in enumerate(nav):
        if i:
            buttons.append(_plain("  "))
        buttons.append(_button(icon_name, text, data, "primary"))
    blocks.append(InputRichBlockParagraph(_concat(*buttons)))
    return InputRichMessage(blocks=blocks)
