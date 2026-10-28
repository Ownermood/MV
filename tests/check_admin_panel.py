import sys, types, importlib.util, asyncio, re
from html.parser import HTMLParser
REPO = sys.argv[1]
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
class Cfg:
    OWNER_ID = 7; DATABASE_URL = "mongodb://x"; START_TEXT = ""; START_IMAGE = ""; START_LINKS = {}; START_GUIDE = True
    PREMIUM_EMOJI = False; USE_IMAGES = False; IMAGES = []; FORCE_SUB_CHATS = []; FORCE_SUB_IDS = ""
    @classmethod
    def set(cls, k, v): setattr(cls, k, v)
saved = {}
auth_saved = []
class DB:
    async def update_config(self, d): saved.update(d)
    async def update_user_data(self, cid): auth_saved.append(cid)
    async def get_pm_uids(self): return [1, 2, 3]
sent, edits, prompts, pm_queue = [], [], [], []
class Msg:
    def __init__(self, text="", photo=None, entities=None): self.text, self.photo, self.entities = text, photo, entities or []
async def send_message(m, text, buttons=None, photo=None, **k):
    if "REJECT" in text: return "Bad Request: can't parse entities"
    r = Msg(text, photo=types.SimpleNamespace(file_id="F") if photo else None); sent.append((m, text, photo)); return r
async def edit_message(m, text, buttons=None, **k):
    m.text, m.markup = text, buttons; edits.append(text)
async def delete_message(m): m.deleted = True
class Str(str):
    @property
    def html(self): return f"<b>{self}</b>"
answers = []
async def ask_in_pm(uid, body): prompts.append(body); return answers.pop(0)
class Bot:
    premium_ok = False
    def add_handler(self, h, group=0): self.h = h; return (h, group)
    def remove_handler(self, *a): pass
    dms = []
    async def send_message(self, uid, text, reply_markup=None):
        Bot.dms.append((uid, text))
        if "Premium emoji test" in text and Bot.premium_ok == "error": raise RuntimeError("BUTTON_ICON_INVALID")
        ents = [types.SimpleNamespace(custom_emoji_id="1")] if Bot.premium_ok is True else []
        return Msg(text, entities=ents)
    cmd_scopes_deleted = []
    async def get_users(self, ref):
        people = {123: "Tom", "@tom": "Tom"}
        if ref not in people: raise ValueError("USER_NOT_FOUND")
        return types.SimpleNamespace(id=123, first_name=people[ref], is_bot=False)
    async def delete_bot_commands(self, scope=None): Bot.cmd_scopes_deleted.append(scope.chat_id)
bot = Bot()
class BM:
    def __init__(s): s.rows = []
    def data_button(s, k, d, position=None, style=None, icon=None): s.rows.append((k, d, style, icon))
    def url_button(s, k, d, position=None, style=None, icon=None): s.rows.append((k, d, style, icon))
    def build_menu(s, *a, **k): return list(s.rows)
bc_calls = []
async def run_broadcast(rply, reply_to, forwarded=False, quietly=False): bc_calls.append((rply, quietly)); return "bc9"
udata = {}
def update_user_ldata(cid, k, v): udata.setdefault(cid, {})[k] = v
mod("bot", LOGGER=types.SimpleNamespace(info=print, warning=print, error=print), sudo_users=[55], bot_start_time=0, task_dict={1: 1}, auth_chats={-1009: []}, user_data=udata); mod("bot.core"); mod("bot.core.config_manager", Config=Cfg)
mod("bot.core.tg_client", TgClient=types.SimpleNamespace(bot=bot))
mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.bot_utils", new_task=lambda f: f, update_user_ldata=update_user_ldata); mod("bot.helper.ext_utils.db_handler", database=DB())
mod("bot.helper.ext_utils.status_utils", get_readable_time=lambda s: "1h")
mod("bot.helper.telegram_helper")
mod("bot.helper.telegram_helper.button_build", ButtonMaker=BM, valid_url=lambda u: u if u.startswith("https://") else None)
mod("bot.helper.telegram_helper.message_utils", send_message=send_message, edit_message=edit_message, delete_message=delete_message)
mod("bot.helper.telegram_helper.prompt", STOP="STOP", PromptUnreachable=type("PU", (Exception,), {}), ask_in_pm=ask_in_pm)
mod("bot.modules"); mod("bot.modules.broadcast", run_broadcast=run_broadcast)
mod("bot.helper.telegram_helper.bot_commands", BotCommands=types.SimpleNamespace(
    admin_menu_set={123}, AuthorizeCommand=["adduser"], UnAuthorizeCommand=["rmuser"],
    AddSudoCommand=["addadmin"], RmSudoCommand=["rmadmin"]))
class CMS: ADMINISTRATOR = "admin"; OWNER = "owner"; MEMBER = "member"
import pyrogram.enums as _en
_en.ChatMemberStatus = CMS
class FChat:
    def __init__(s, cid, title, username=None, admin=True): s.id, s.title, s.username, s.invite_link, s.admin = cid, title, username, None, admin
    async def get_member(s, who): return types.SimpleNamespace(status=CMS.ADMINISTRATOR if s.admin else CMS.MEMBER)
fchats = {"-1001": FChat(-1001, "Main Channel", "mainch"), "@grp": FChat(-1002, "Private Grp", None, admin=False)}
async def chat_info(cid): return fchats.get(str(cid))
cleared = []
def fsub_chats():
    return [{"id": str(c["id"]), "name": c.get("name", ""), "link": c.get("link", "")} for c in Cfg.FORCE_SUB_CHATS] + [{"id": i, "name": "", "link": ""} for i in Cfg.FORCE_SUB_IDS.split()]
mod("bot.helper.telegram_helper.force_join", fsub_chats=fsub_chats, clear_join_cache=lambda: cleared.append(1))
mod("bot.helper.telegram_helper.tg_utils", chat_info=chat_info)
menu_calls = []
async def ensure_admin_menu(uid): menu_calls.append(uid)
mod("bot.modules.services", start_home=lambda u: ("HOME", []), start_photo=lambda: "IMAGES", ensure_admin_menu=ensure_admin_menu)
for name, path in (("bot.helper.telegram_helper.emoji", "bot/helper/telegram_helper/emoji.py"), ("bot.helper.telegram_helper.rich_name", "bot/helper/telegram_helper/rich_name.py"), ("bot.modules.admin_panel", "bot/modules/admin_panel.py"), ("bot.modules.chat_permission", "bot/modules/chat_permission.py")):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
ap = sys.modules["bot.modules.admin_panel"]
async def wait_pm(uid, timeout=120): return pm_queue.pop(0) if pm_queue else None
ap._wait_pm = wait_pm
ap.Message = Msg
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
allowed = {"b", "i", "code", "a", "u", "s", "pre", "blockquote", "tg-emoji", "tg-spoiler"}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.bad = []
    def handle_starttag(s, tg, a): (s.bad.append(tg) if tg not in allowed else None); s.stack.append(tg)
    def handle_endtag(s, tg): s.bad.append("unbalanced " + tg) if not s.stack or s.stack.pop() != tg else None
def valid(text, rows):
    p = P(); p.feed(text)
    return not p.bad and not p.stack and len(text) <= 4096 and all(len(r[1].encode()) <= 64 for r in rows)
class Q:
    def __init__(s, data, msg, uid=7): s.data, s.message, s.from_user, s.alerts = data, msg, types.SimpleNamespace(id=uid), []
    async def answer(s, text=None, show_alert=False): s.alerts.append(text)
async def main():
    m = Msg(); await ap.admin_panel(None, types.SimpleNamespace(from_user=types.SimpleNamespace(id=7)))
    home_text, home_rows = sent[-1][1], None
    t("opening /admin sets the admin command menu", menu_calls == [7])
    t("home shows users/tasks", "Users:</b> <code>3</code>" in home_text and "Running tasks:</b> <code>1</code>" in home_text)
    async def click(data, uid=7):
        q = Q(data, m, uid); await ap.admin_panel_cb(None, q); return q
    for prem in (False, True):
        Cfg.PREMIUM_EMOJI = prem
        for page in ("home", "text", "img", "btns", "bc", "prem", "fj", "grp", "acc", "admins", "usr"):
            await click(f"adm 7 {page}")
            t(f"page {page} valid (premium={prem})", valid(m.text, m.markup) and all(r[2] in (ap.GREEN, ap.ButtonStyle.PRIMARY, ap.ButtonStyle.DANGER) for r in m.markup) and all(r[2] == ap.ButtonStyle.DANGER for r in m.markup if r[1].endswith(" close")))
    Cfg.PREMIUM_EMOJI = False
    q = await click("adm 7 home", uid=8); t("other admin blocked", q.alerts and "another admin" in q.alerts[0])
    answers.append(Str("Welcome to my bot")); await click("adm 7 text_set")
    t("welcome text saved with formatting", saved.get("START_TEXT") == "<b>Welcome to my bot</b>" and "Saved" in m.text)
    answers.append(Str("x" * 950)); await click("adm 7 text_set"); t("too long text refused", "Too long" in m.text and saved["START_TEXT"] == "<b>Welcome to my bot</b>")
    answers.append(Str("REJECT")); await click("adm 7 text_set")
    t("text Telegram rejects is not saved", "rejected" in m.text)
    await click("adm 7 text_reset"); t("text reset", saved["START_TEXT"] == "")
    pm_queue.append(Msg(photo=types.SimpleNamespace(file_id="PHOTO123"))); await click("adm 7 img_set")
    t("image saved from photo", saved.get("START_IMAGE") == "PHOTO123")
    pm_queue.append(Msg(text="not a url")); await click("adm 7 img_set"); t("bad image refused", "not a photo" in m.text and saved["START_IMAGE"] == "PHOTO123")
    await click("adm 7 img_reset"); t("image removed", saved["START_IMAGE"] == "")
    answers.extend([Str("📢 Updates"), Str("t.me/mychannel")]); await click("adm 7 link_add")
    t("link added (t.me normalized)", saved.get("START_LINKS") == {"📢 Updates": "https://t.me/mychannel"})
    answers.extend([Str("Bad"), Str("javascript:x")]); await click("adm 7 link_add"); t("invalid link refused", len(saved["START_LINKS"]) == 1)
    await click("adm 7 link_rm 0"); t("link removed", saved["START_LINKS"] == {})
    await click("adm 7 tog_guide")
    t("guide toggle saved", saved["START_GUIDE"] is False)
    guide_btn = [r for r in m.markup if r[1] == "adm 7 tog_guide"][0]
    t("OFF toggle is blue", guide_btn[2] == ap.ButtonStyle.PRIMARY)
    await click("adm 7 tog_guide")
    guide_btn = [r for r in m.markup if r[1] == "adm 7 tog_guide"][0]
    t("ON toggle is green", guide_btn[2] == ap.GREEN)
    t("no source code toggle anywhere", not any("tog_src" in r[1] for r in m.markup))
    Bot.premium_ok = "error"; await click("adm 7 prem_tog"); t("premium rejected -> stays off", Cfg.PREMIUM_EMOJI is False and "rejected" in m.text)
    Bot.premium_ok = False; await click("adm 7 prem_tog"); t("premium silently stripped -> stays off", Cfg.PREMIUM_EMOJI is False and "not available" in m.text)
    Bot.premium_ok = True; await click("adm 7 prem_tog"); t("premium accepted -> on", Cfg.PREMIUM_EMOJI is True)
    await click("adm 7 home"); t("panel uses premium tags when on", "tg-emoji" in m.text and valid(m.text, m.markup))
    await click("adm 7 prem_tog"); t("premium off again", Cfg.PREMIUM_EMOJI is False)
    bmsg = Msg(text="Hello all"); pm_queue.append(bmsg); await click("adm 7 bc_new")
    t("broadcast asks confirmation", "Confirm broadcast" in m.text and not bc_calls)
    await click("adm 7 bc_go 1"); t("broadcast sent silently", bc_calls == [(bmsg, True)] and "bc9" in m.text)
    await click("adm 7 bc_go 0"); t("no double send", len(bc_calls) == 1 and "Nothing to send" in m.text)
    fwd = Msg(); fwd.forward_origin = types.SimpleNamespace(chat=types.SimpleNamespace(id="-1001")); fwd.forward_from_chat = None
    pm_queue.append(fwd); answers.extend([Str("skip"), Str("skip")]); await click("adm 7 fj_add")
    t(f"force join from forwarded msg, auto name+link", saved.get("FORCE_SUB_CHATS") == [{"id": "-1001", "name": "Main Channel", "link": "https://t.me/mainch"}] and cleared)
    pm_queue.append(Msg(text="@grp")); answers.extend([Str("Our Group"), Str("skip")]); await click("adm 7 fj_add")
    t("private chat without link refused", len(saved["FORCE_SUB_CHATS"]) == 1 and "valid join link" in m.text)
    pm_queue.append(Msg(text="@grp")); answers.extend([Str("Our Group"), Str("t.me/+secret")]); await click("adm 7 fj_add")
    t("private chat added with link + not-admin warning", saved["FORCE_SUB_CHATS"][-1] == {"id": "-1002", "name": "Our Group", "link": "https://t.me/+secret"} and "not an admin" in m.text)
    pm_queue.append(Msg(text="-999")); await click("adm 7 fj_add"); t("unknown chat refused", "can't open" in m.text and len(saved["FORCE_SUB_CHATS"]) == 2)
    await click("adm 7 fj"); t("force join page valid", valid(m.text, m.markup) and "Our Group" in m.text)
    await click("adm 7 fj_rm 0"); t("force join chat removed", [c["id"] for c in saved["FORCE_SUB_CHATS"]] == ["-1002"])
    pm_queue.append(Msg(text="-1001")); await click("adm 7 grp_add")
    t("group authorized from panel", udata.get(-1001, {}).get("AUTH") is True and -1001 in auth_saved)
    await click("adm 7 grp"); t(f"groups page lists config + panel groups", "-1009" in m.text and "from config" in m.text and "-1001" in m.text and valid(m.text, m.markup))
    t("config group has no remove button", not any("Remove" in r[0] and "-1009" in r[0] for r in m.markup))
    await click("adm 7 grp_rm -1001"); t("group removed", udata[-1001]["AUTH"] is False)
    pm_queue.append(Msg(text="nope")); await click("adm 7 grp_add"); t("unknown group refused", "can't open" in m.text)
    # access: admins (owner only) and allowed users
    pm_queue.extend([Msg(text="123"), Msg(text="Tommy")]); await click("adm 7 adm_add")
    t("admin added with custom name", udata[123].get("SUDO") is True and udata[123].get("PANEL_NAME") == "Tommy" and 123 in menu_calls)
    await click("adm 7 admins")
    t("admins page: owner, config and panel admins", "Tommy" in m.text and "from config" in m.text and "<code>55</code>" in m.text and "owner" in m.text and valid(m.text, m.markup))
    t("only panel admins have remove buttons", [r[1] for r in m.markup if "adm_rm" in r[1]] == ["adm 7 adm_rm 123"])
    pm_queue.append(Msg(text="Tom B")); await click("adm 7 adm_name 123"); t("admin renamed", udata[123]["PANEL_NAME"] == "Tom B")
    t("new admin gets a DM", any(u == 123 and "You are now an admin" in x and "Tommy" in x for u, x in Bot.dms))
    pm_queue.append(Msg(text="Wifu 8494053059")); await click("adm 7 adm_add")
    t("'Name ID' in one message, ID unknown to the bot still works", udata[8494053059].get("SUDO") is True and udata[8494053059]["PANEL_NAME"] == "Wifu" and not pm_queue)
    t("prompt shows the Name ID example", any("Wifu 8494053059" in x for _, x, _ in sent))
    sudo_m = Msg(); q = Q("adm 8 adm_add", sudo_m, 8); await ap.admin_panel_cb(None, q)
    t("sudo cannot add admins", "Only the owner" in sudo_m.text and len(pm_queue) == 0)
    await click("adm 7 adm_rm 7"); t("owner cannot be removed", "removed" not in m.text)
    await click("adm 7 adm_rm 123")
    t("admin removed and their command menu cleared", udata[123]["SUDO"] is False and 123 in Bot.cmd_scopes_deleted)
    t("removed admin gets a DM", any(u == 123 and "no longer an admin" in x for u, x in Bot.dms))
    fwd = Msg(text=""); fwd.forward_from = types.SimpleNamespace(id=456, first_name="Ann", is_bot=False)
    pm_queue.extend([fwd, Msg(text="/skip")]); await click("adm 7 usr_add")
    t("user allowed from a forward, Telegram name kept", udata[456].get("AUTH") is True and udata[456]["PANEL_NAME"] == "Ann")
    await click("adm 7 usr"); t("users page lists them", "Ann" in m.text and "<code>456</code>" in m.text and valid(m.text, m.markup))
    await click("adm 7 usr_rm 456"); t("user removed", udata[456]["AUTH"] is False)
    pm_queue.append(Msg(text="@nobody")); await click("adm 7 usr_add"); t("unknown user refused", "not found" in m.text)
    # commands: /addadmin Name ID with premium emoji, /rmadmin, /adduser, /rmuser
    from pyrogram.enums import ChatType, MessageEntityType
    from pyrogram.types import MessageEntity
    cp = sys.modules["bot.modules.chat_permission"]
    def cmd(text, entities=(), reply=None):
        return types.SimpleNamespace(text=text, entities=list(entities), reply_to_message=reply,
                                     chat=types.SimpleNamespace(type=ChatType.PRIVATE, id=7),
                                     message_thread_id=None, is_topic_message=False)
    await cp.add_sudo(None, cmd("/addadmin"))
    t("/addadmin alone shows the easy usage", "/addadmin Wifu 8494053059" in sent[-1][1])
    star = MessageEntity(type=MessageEntityType.CUSTOM_EMOJI, offset=15, length=1, custom_emoji_id=5444939047132755535)
    await cp.add_sudo(None, cmd("/addadmin Wifu ⭐ 8494050001", [star]))
    nm = udata[8494050001].get("PANEL_NAME", "")
    t(f"/addadmin keeps premium emoji in the name ({nm})", udata[8494050001].get("SUDO") is True and nm == 'Wifu <tg-emoji emoji-id="5444939047132755535">⭐</tg-emoji>')
    t("new admin got the DM with the tag", any(u == 8494050001 and "tg-emoji" in x for u, x in Bot.dms) and "is now an admin" in sent[-1][1])
    await cp.add_sudo(None, cmd("/addadmin Boss <b> 8494050001"))
    t("name with HTML is escaped", udata[8494050001]["PANEL_NAME"] == "Boss &lt;b&gt;" and "Name updated" in sent[-1][1])
    reply = types.SimpleNamespace(id=99, from_user=types.SimpleNamespace(id=8494050002, first_name="Rex"), sender_chat=None)
    await cp.add_sudo(None, cmd("/addadmin", reply=reply))
    t("/addadmin as a reply uses their Telegram name", udata[8494050002]["SUDO"] is True and udata[8494050002]["PANEL_NAME"] == "Rex")
    await cp.remove_sudo(None, cmd("/rmadmin 8494050001")); t("/rmadmin removes", udata[8494050001]["SUDO"] is False)
    await cp.remove_sudo(None, cmd("/rmadmin 7")); t("/rmadmin cannot remove the owner", "config.py" in sent[-1][1])
    await cp.authorize(None, cmd("/adduser Ann 8494050003")); t("/adduser Name ID", udata[8494050003]["AUTH"] is True and udata[8494050003]["PANEL_NAME"] == "Ann")
    await cp.unauthorize(None, cmd("/rmuser 8494050003")); t("/rmuser", udata[8494050003]["AUTH"] is False)
    await click("adm 7 close"); t("close deletes panel", getattr(m, "deleted", False))
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
