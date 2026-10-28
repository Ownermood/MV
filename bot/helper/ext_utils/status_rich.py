# Rich message version of the status card (Telegram rich messages): key/value
# tables, dividers and coloured buttons inside the text. Built from the same
# data as the HTML card; callers fall back to HTML when sending this fails.
from pyrogram import raw
from pyrogram.types import (
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockTable,
    InputRichBlockTableCell,
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


def _button(text, data, style):
    return raw.types.TextButton(
        text=_plain(text),
        type=raw.types.InlineButtonTypeCallback(data=data.encode()),
        style=raw.types.RichButtonStyle(**{f"bg_{style}": True}),
    )


def _cell(text, bold=False, right=False):
    return InputRichBlockTableCell(
        _concat(_bold(text) if bold else _plain(text)), align_right=right or None
    )


def build_rich_status(header, tasks, stats):
    """header: text line; tasks: dicts from get_readable_message; stats: (key, value)."""
    blocks = [
        InputRichBlockParagraph(
            _concat(_emoji("list"), _plain(" "), raw.types.TextMarked(text=_bold(header)))
        )
    ]
    for task in tasks:
        blocks.append(InputRichBlockDivider())
        blocks.append(
            InputRichBlockParagraph(
                _concat(_emoji(task["icon"]), _plain(" "), _bold(task["title"]))
            )
        )
        name = task["name"] + (f"\n↳ {task['sub']}" if task["sub"] else "")
        blocks.append(InputRichBlockParagraph(raw.types.TextItalic(text=_plain(name))))
        if task["bar"]:
            blocks.append(
                InputRichBlockParagraph(_concat(_plain(f"{task['bar']} "), _bold(task["pct"])))
            )
        rows = [[_cell(k, bold=True), _cell(v, right=True)] for k, v in task["fields"]]
        user_name, user_id = task["user"]
        rows.append(
            [
                _cell("User", bold=True),
                InputRichBlockTableCell(
                    raw.types.TextUrl(
                        text=_plain(f"{user_name} ({user_id})"),
                        url=f"tg://user?id={user_id}",
                        webpage_id=0,
                    ),
                    align_right=True,
                ),
            ]
        )
        blocks.append(InputRichBlockTable(title=_plain(""), rows=rows, compact=True))
        actions = [_button("Cancel Task", f"rcan {task['gid']}", "danger")]
        if task["select"]:
            actions += [_plain("  "), _button("Select Files", f"rsel {task['gid']}", "primary")]
        blocks.append(InputRichBlockParagraph(_concat(*actions)))
    blocks.append(InputRichBlockDivider())
    blocks.append(
        InputRichBlockParagraph(_concat(_emoji("chart"), _plain(" "), _bold("Bot Stats")))
    )
    blocks.append(
        InputRichBlockTable(
            title=_plain(""),
            rows=[[_cell(k, bold=True), _cell(v, right=True)] for k, v in stats],
            compact=True,
        )
    )
    return InputRichMessage(blocks=blocks)
