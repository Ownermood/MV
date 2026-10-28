"""Task errors: full text to the user's DM and ERROR_LOG_CHAT, nothing in the
group unless the DM fails (then a short reason), never the full one there."""
import asyncio, importlib.util, sys, types

from pyrogram.enums import ChatType

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


class Cfg: PREMIUM_EMOJI = False; ERROR_LOG_CHAT = "-100777"


sent = []
UNREACHABLE = {555}


async def send_message(chat, text, buttons=None, **k):
    target = chat if isinstance(chat, (int, str)) else ("reply", chat.chat.id)
    if target in UNREACHABLE:
        return "Bad Request: chat not found"
    sent.append((target, text)); return object()


mod("bot", LOGGER=types.SimpleNamespace(warning=print, info=print))
mod("bot.core"); mod("bot.core.config_manager", Config=Cfg)
mod("bot.helper"); mod("bot.helper.telegram_helper")
mod("bot.helper.telegram_helper.message_utils", send_message=send_message)
for name, path in (("bot.helper.telegram_helper.emoji", "bot/helper/telegram_helper/emoji.py"),
                   ("bot.helper.telegram_helper.error_report", "bot/helper/telegram_helper/error_report.py")):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
er = sys.modules["bot.helper.telegram_helper.error_report"]


def listener(user_id, chat_id, kind=ChatType.SUPERGROUP):
    chat = types.SimpleNamespace(id=chat_id, username=None, type=kind)
    msg = types.SimpleNamespace(chat=chat, link="https://t.me/c/1/2", from_user=types.SimpleNamespace(mention="@user"))
    return types.SimpleNamespace(message=msg, user_id=user_id, tag="@user", link="https://youtu.be/x")


YT = "ERROR: [youtube] rC-kbRanJQ0: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies"
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)


sent.clear(); asyncio.run(er.report_task_error(listener(111, -100500), YT))
targets = [x for x, _ in sent]
t("group task: full error in DM and log chat, nothing in the group", targets == [-100777, 111] and "Sign in to confirm" in sent[1][1])
t("log chat message links the task", "Task message" in sent[0][1])

sent.clear(); asyncio.run(er.report_task_error(listener(555, -100500), YT))
t("DM not possible: short reason in the group instead", [x for x, _ in sent] == [-100777, ("reply", -100500)])
t("short reason is plain words", "owner needs to add YouTube cookies" in sent[1][1] and "--cookies" not in sent[1][1])

sent.clear(); asyncio.run(er.report_task_error(listener(111, 111, ChatType.PRIVATE), "boom"))
t("task started in DM: full error there", [x for x, _ in sent] == [-100777, ("reply", 111)])

Cfg.ERROR_LOG_CHAT = "-100500"
sent.clear(); asyncio.run(er.report_task_error(listener(111, -100500), "boom"))
t("log chat = the task's group: full error not posted there", [x for x, _ in sent] == [111])

sent.clear(); asyncio.run(er.report_task_error(listener(111, -1), "<b>bold</b> a < b & c"))
t("tags in errors are removed, < & are escaped", "a &lt; b &amp; c" in sent[-1][1] and "<b>bold" not in sent[-1][1])
print("ALL PASS" if ok else "SOME FAILED")
