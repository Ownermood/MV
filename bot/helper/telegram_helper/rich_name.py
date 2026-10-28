# Names typed by the owner (admin tags, user names) may contain premium emoji.
# Keep only those as <tg-emoji> and escape everything else, so the stored name
# is safe to put into any HTML message.
from html import escape, unescape
from re import fullmatch, sub

from pyrogram.enums import MessageEntityType
from pyrogram.parser.utils import add_surrogates, remove_surrogates


def name_html(text, entities=None, start=0, end=None):
    """HTML for text[start:end] (Python indexes) keeping its premium emoji."""
    text = text or ""
    end = len(text) if end is None else end
    s = add_surrogates(text)
    lo, hi = len(add_surrogates(text[:start])), len(add_surrogates(text[:end]))
    emojis = sorted(
        (en for en in entities or () if en.type == MessageEntityType.CUSTOM_EMOJI
         and lo <= en.offset and en.offset + en.length <= hi),
        key=lambda en: en.offset,
    )
    out, pos = [], lo
    for en in emojis:
        out.append(escape(remove_surrogates(s[pos:en.offset])))
        char = escape(remove_surrogates(s[en.offset:en.offset + en.length]))
        out.append(f'<tg-emoji emoji-id="{int(en.custom_emoji_id)}">{char}</tg-emoji>')
        pos = en.offset + en.length
    out.append(escape(remove_surrogates(s[pos:hi])))
    return "".join(out).strip()


def name_plain(html):
    """Text of a stored name for places without HTML (button labels)."""
    return unescape(sub(r"<[^>]+>", "", html or "")).strip()


def split_name_and_id(message, skip_words=1):
    """'/addadmin Wifu 🌸 8494053059' -> ('Wifu <tg-emoji…>🌸</tg-emoji>', '8494053059').
    The last word is the ID or @username when it looks like one; skip_words
    drops the command itself."""
    text = message.text or ""
    spans, pos = [], 0
    for word in text.split():
        pos = text.find(word, pos)
        spans.append((word, pos))
        pos += len(word)
    rest = spans[skip_words:]
    if not rest:
        return "", ""
    ref, end = "", len(text)
    last, last_at = rest[-1]
    if fullmatch(r"-?\d+(\|\d+)?", last) or last.startswith("@"):
        ref, end = last, last_at
    html = name_html(text, message.entities, rest[0][1], end)
    if len(name_plain(html)) > 32 or len(html) > 1000:
        html = escape(name_plain(html)[:32])
    return html, ref
