import sys, types, importlib.util, asyncio
REPO = sys.argv[1]
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
from pyrogram.errors import RPCError, UserNotParticipant  # real classes
class Cfg: FORCE_SUB_CHATS = []; FORCE_SUB_IDS = ""; PREMIUM_EMOJI = False
STYLES = []
members = {"-1001": {5}, "-1002": set()}
calls = []
class Chat:
    def __init__(s, cid, title, username=None, invite=None): s.id, s.title, s.username, s.invite_link = cid, title, username, invite
    async def get_member(s, uid):
        calls.append((s.id, uid))
        if s.id == "-1003": raise RPCError()
        if uid not in members[s.id]: raise UserNotParticipant()
chats = {"-1001": Chat("-1001", "Main", "mainch"), "-1002": Chat("-1002", "Private Group", None, "https://t.me/+abc"), "-1003": Chat("-1003", "NotAdmin")}
async def chat_info(cid): return chats.get(str(cid))
class Sudo:
    async def __call__(self, _, update): return update.from_user.id == 1
class BM:
    def __init__(s): s.rows = []
    def url_button(s, k, d, position=None, style=None, icon=None): s.rows.append((k, d)); STYLES.append(style)
    def data_button(s, k, d, position=None, style=None, icon=None): s.rows.append((k, d))
    def build_menu(s, *a, **k): return s.rows
mod("bot", LOGGER=types.SimpleNamespace(warning=lambda *a: None)); mod("bot.core"); mod("bot.core.config_manager", Config=Cfg)
mod("bot.helper"); mod("bot.helper.telegram_helper")
import pyrogram.filters as _pf
_pf.create = lambda f: f
mod("bot.helper.telegram_helper.button_build", ButtonMaker=BM)
mod("bot.helper.telegram_helper.filters", CustomFilters=types.SimpleNamespace(sudo=Sudo()))
mod("bot.helper.telegram_helper.tg_utils", chat_info=chat_info)
for name, path in (("bot.helper.telegram_helper.emoji", "emoji.py"), ("bot.helper.telegram_helper.force_join", "force_join.py")):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/helper/telegram_helper/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
fj = sys.modules["bot.helper.telegram_helper.force_join"]
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
def upd(uid): return types.SimpleNamespace(from_user=types.SimpleNamespace(id=uid), sender_chat=None)
async def main():
    t("no chats -> nobody blocked", await fj._not_joined(None, None, upd(9)) is False)
    Cfg.FORCE_SUB_CHATS = [{"id": "-1001", "name": "📢 Updates", "link": ""}, {"id": "-1002", "name": "", "link": ""}]
    Cfg.FORCE_SUB_IDS = "-1001 -1003"
    t("legacy ids merged without duplicates", [c["id"] for c in fj.fsub_chats()] == ["-1001", "-1002", "-1003"])
    miss = await fj.missing_chats(9)
    t(f"user 9 missing both, names/links from config or chat {miss}", miss == [("📢 Updates", "https://t.me/mainch"), ("Private Group", "https://t.me/+abc")])
    t("bot not admin in -1003 does not block", all(n != "NotAdmin" for n, _ in miss))
    t("gate blocks user 9", await fj._not_joined(None, None, upd(9)) is True)
    t("sudo/owner never blocked", await fj._not_joined(None, None, upd(1)) is False)
    members["-1002"].add(9); members["-1001"].add(9)
    t("joined user passes", await fj.missing_chats(9) == [])
    n = len(calls); await fj.missing_chats(9)
    t("joined result cached (no API calls)", len(calls) == n)
    members["-1001"].discard(9)
    t("cache bypass sees leaving", await fj.missing_chats(9, use_cache=False) == [("📢 Updates", "https://t.me/mainch")])
    fj.clear_join_cache()
    markup = fj.join_markup(9, [("📢 Updates", "https://t.me/mainch"), ("NoLink", None)])
    t(f"join buttons + I've Joined {markup}", markup == [("➕ 📢 Updates", "https://t.me/mainch"), ("✅ I've Joined", "fsub 9")])
    import pyrogram.enums as pe
    t(f"join buttons are green {STYLES}", STYLES == [pe.ButtonStyle.SUCCESS])
    txt = fj.join_text([("A&B <x>", "l")])
    t("join text escapes chat names", "A&amp;B &lt;x&gt;" in txt)
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
