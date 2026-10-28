import sys, types, importlib.util, asyncio, json, os
REPO, WORK = sys.argv[1], sys.argv[2]
os.chdir(WORK)
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
# in-memory remote "gd": {path: size or None for dir}
FS = {"gd": {"Movies": None, "Movies/a.mkv": 100, "Movies/b.mkv": 200, "notes.txt": 5}}
calls = []
def _children(rem, path):
    pre = f"{path}/" if path else ""
    out = []
    for p, sz in FS[rem].items():
        if p.startswith(pre) and "/" not in p[len(pre):]:
            out.append({"Name": p[len(pre):], "Size": sz or -1, "IsDir": sz is None})
    return out
async def cmd_exec(cmd, shell=False):
    calls.append(cmd); a = cmd[1:]
    def target(x): r, p = x.split(":", 1); return r, p
    if a[0] == "listremotes": return "gd:\n", "", 0
    if a[0] == "lsjson": r, p = target(a[-1]); return json.dumps(_children(r, p)), "", 0
    if a[0] == "about": return json.dumps({"total": 1000, "used": 305, "free": 695, "trashed": 0}), "", 0
    if a[0] == "size":
        r, p = target(a[-1]); files = [s for k, s in FS[r].items() if s and (not p or k.startswith(p + "/"))]
        return json.dumps({"count": len(files), "bytes": sum(files)}), "", 0
    if a[0] == "mkdir": r, p = target(a[-1]); FS[r][p] = None; return "", "", 0
    if a[0] == "moveto":
        r, src = target(a[-2]); _, dst = target(a[-1]); FS[r][dst] = FS[r].pop(src); return "", "", 0
    if a[0] == "deletefile": r, p = target(a[-1]); FS[r].pop(p); return "", "", 0
    if a[0] == "purge":
        r, p = target(a[-1])
        for k in [k for k in FS[r] if k == p or k.startswith(p + "/")]: FS[r].pop(k)
        return "", "", 0
    if a[0] == "cleanup": return "", "trash not supported", 1
    if a[0] == "dedupe": return "", "", 0
    return "", "unknown", 1
class Sudo:
    async def __call__(self, *a): return SUDO["v"]
SUDO = {"v": False}
answers = []
async def ask_in_pm(uid, body, timeout=120, extra=None): return answers.pop(0)
class PromptUnreachable(Exception): pass
edits = []
class Msg:
    def __init__(self, uid=5): self.from_user = types.SimpleNamespace(id=uid); self.text = ""; self.markup = None
async def edit_message(m, text, buttons=None, **k):
    m.text, m.markup = text, buttons; edits.append(text); return m
async def send_message(m, text, buttons=None, **k):
    r = Msg(); r.text, r.markup = text, buttons; return r
def new_task(f): return f
class BM:
    def __init__(self): self.b = []
    def data_button(self, k, d, position=None, style=None): self.b.append((k, d))
    def build_menu(self, *a, **k): return list(self.b)
mod("bot"); mod("bot.core"); mod("bot.core.config_manager", BinConfig=type("B", (), {"RCLONE_NAME": "rclone"}), Config=type("C", (), {"OWNER_ID": 1}))
mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.bot_utils", cmd_exec=cmd_exec, new_task=new_task, safe_path_name=lambda n: ("" if (n := str(n).replace("/", "_").replace("\\", "_").strip()) in (".", "..") else n))
mod("bot.helper.ext_utils.status_utils", get_readable_file_size=lambda b: f"{b}B")
mod("bot.helper.telegram_helper"); mod("bot.helper.telegram_helper.button_build", ButtonMaker=BM)
mod("bot.helper.telegram_helper.filters", CustomFilters=type("CF", (), {"sudo": Sudo()}))
mod("bot.helper.telegram_helper.message_utils", edit_message=edit_message, send_message=send_message)
mod("bot.helper.telegram_helper.prompt", STOP="STOP", PromptUnreachable=PromptUnreachable, ask_in_pm=ask_in_pm)
mod("bot.modules")
name = "bot.modules.rclone_fm"
spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/modules/rclone_fm.py")
fm = importlib.util.module_from_spec(spec); sys.modules[name] = fm; spec.loader.exec_module(fm)
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
class Q:
    def __init__(self, data, msg, uid=5): self.data, self.message, self.from_user = data, msg, types.SimpleNamespace(id=uid); self.alerts = []
    async def answer(self, text=None, show_alert=False): self.alerts.append(text)
def btn(msg, label_start):
    return next(d for k, d in msg.markup if k.startswith(label_start))
async def main():
    # no config -> refused
    m = Msg(); r = await fm.rclone_fm(None, m)
    t("no rclone config -> asked to upload", True)
    # normal user cannot use owner rclone.conf
    open("rclone.conf", "w").write("[gd]\ntype=drive\n")
    sent = []
    global send_message
    async def sm(mm, text, buttons=None, **k):
        r = Msg(); r.text, r.markup = text, buttons; sent.append(r); return r
    fm.send_message = sm
    await fm.rclone_fm(None, Msg())
    t(f"normal user, only owner conf -> refused: {sent[-1].text[:40]!r}", "Upload your rclone.conf" in sent[-1].text)
    SUDO["v"] = True
    await fm.rclone_fm(None, Msg())
    menu = sent[-1]
    t(f"sudo gets owner conf -> remotes list {menu.markup}", ("gd", "rcfm 5 rem 0") in menu.markup)
    async def click(data, uid=5):
        q = Q(data, menu, uid); await fm.rclone_fm_cb(None, q); return q
    q = await click("rcfm 5 rem 0", uid=9)
    t("other user's click rejected", q.alerts and "not for you" in q.alerts[0])
    await click("rcfm 5 rem 0"); t("remote menu", "Remote:" in menu.text)
    await click("rcfm 5 about"); t(f"storage: {menu.text!r}", "Used:</b> 305B" in menu.text and "Total:</b> 1000B" in menu.text)
    await click("rcfm 5 trash"); t("trash asks confirmation", "Permanently empty" in menu.text and not any(c[1] == "cleanup" for c in calls))
    await click("rcfm 5 trashy"); t(f"cleanup error shown: {menu.text[:60]!r}", "trash not supported" in menu.text)
    await click("rcfm 5 ls"); t("root listing: dirs first", [k for k, d in menu.markup if k.startswith(("📁", "📄"))] == ["📁 Movies", "📄 notes.txt"])
    await click("rcfm 5 it 0"); t(f"enter folder: {menu.text[:40]!r}", "gd:Movies" in menu.text)
    await click("rcfm 5 size"); t(f"folder size: {menu.text!r}", "Files:</b> 2" in menu.text and "300B" in menu.text)
    await click("rcfm 5 ls")
    answers.append("../../etc")
    await click("rcfm 5 mk")
    t("mkdir rejects traversal name", not any(c[1] == "mkdir" for c in calls))
    answers.append("Season 1")
    await click("rcfm 5 mk")
    t(f"mkdir args {calls[-2]}", ["rclone", "mkdir", "--config", "rclone.conf", "gd:Movies/Season 1"] in calls and "Movies/Season 1" in FS["gd"])
    idx = [k for k, d in menu.markup].index("📄 a.mkv") - [k for k, d in menu.markup].index("📁 Season 1") + 0
    items = [i["Name"] for i in fm.fm_state[5]["items"]]
    ia = items.index("a.mkv")
    await click(f"rcfm 5 it {ia}"); t("file menu", "File:</b> <code>Movies/a.mkv" in menu.text)
    answers.append("A Movie.mkv")
    await click(f"rcfm 5 rn {ia}")
    t("rename via moveto", ["rclone", "moveto", "--config", "rclone.conf", "gd:Movies/a.mkv", "gd:Movies/A Movie.mkv"] in calls)
    items = [i["Name"] for i in fm.fm_state[5]["items"]]
    ib = items.index("b.mkv")
    await click(f"rcfm 5 rm {ib}"); t("delete asks confirmation", "Delete <code>b.mkv" in menu.text and "Movies/b.mkv" in FS["gd"])
    await click(f"rcfm 5 rmy {ib}"); t("deletefile ran", "Movies/b.mkv" not in FS["gd"])
    await click("rcfm 5 rmdir"); t("delete folder asks confirmation", "and everything in it" in menu.text)
    await click("rcfm 5 rmdiry"); t(f"purge ran + back to parent: {menu.text[:30]!r}", not any(k.startswith("Movies") for k in FS["gd"]) and "gd:</code>" in menu.text)
    await click("rcfm 5 it 99"); t("stale index handled", "out of date" in menu.text)
    await click("rcfm 5 close"); t("close clears state", 5 not in fm.fm_state)
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
