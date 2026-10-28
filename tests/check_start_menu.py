import ast, sys, types, importlib.util, re
from html.parser import HTMLParser
REPO = sys.argv[1]
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
class Cfg: PREMIUM_EMOJI = False; START_TEXT = ""
mod("bot"); mod("bot.core"); mod("bot.core.config_manager", Config=Cfg); mod("bot.helper"); mod("bot.helper.telegram_helper")
spec = importlib.util.spec_from_file_location("bot.helper.telegram_helper.emoji", f"{REPO}/bot/helper/telegram_helper/emoji.py")
em = importlib.util.module_from_spec(spec); sys.modules[spec.name] = em; spec.loader.exec_module(em)
src = open(f"{REPO}/bot/modules/services.py").read(); tree = ast.parse(src)
want = {"_cmd", "_guide_text", "GUIDE_BUTTONS", "_greeting", "start_body"}
body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in want) or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") in want)]
bc = ast.parse(open(f"{REPO}/bot/helper/telegram_helper/bot_commands.py").read())
table = [ast.literal_eval(n.value) for n in ast.walk(bc) if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "_static_commands"][0]
class BotCommands: pass
for k, v in table.items(): setattr(BotCommands, f"{k}Command", v)
lang_ns = {}; exec(open(f"{REPO}/bot/helper/languages/en.py").read(), lang_ns)
from html import escape
ns = {"BotCommands": BotCommands, "escape": escape, "Config": Cfg, "e": em.e, "Language": lambda: types.SimpleNamespace(**{k: v for k, v in lang_ns.items() if k.isupper()})}
exec(compile(ast.Module(body=body, type_ignores=[]), "x", "exec"), ns)
allowed = {"b", "i", "code", "a", "u", "s", "pre", "blockquote", "tg-emoji", "tg-spoiler"}
class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.bad = []
    def handle_starttag(s, tg, a): (s.bad.append(tg) if tg not in allowed else None); s.stack.append(tg)
    def handle_endtag(s, tg): s.bad.append("unbalanced " + tg) if not s.stack or s.stack.pop() != tg else None
ok = True
user = types.SimpleNamespace(id=8403136096, first_name="Owner <Mood>")
for prem in (False, True):
    Cfg.PREMIUM_EMOJI = prem
    texts = {"home": ns["_greeting"](user) + ns["start_body"]()} | {p: ns["_guide_text"](p) for _, _, p in ns["GUIDE_BUTTONS"]}
    for name, txt in texts.items():
        p = P(); p.feed(txt)
        raw = re.findall(r"&(?![a-z]+;|#\d+;)", txt)
        good = len(txt) <= 1024 and not p.bad and not p.stack and not raw and (("tg-emoji" in txt) == prem)
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} premium={prem!s:5} {name:9} {len(txt):4} chars")
for _, _, page in ns["GUIDE_BUTTONS"]:
    ok &= len(f"guide 8403136096 {page}".encode()) <= 64
print("ALL PASS" if ok else "SOME FAILED")
