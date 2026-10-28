"""Bot Settings sections/search: every variable is reachable, values stay hidden,
pages and callback data fit Telegram limits."""
import importlib.util, sys, types
from html.parser import HTMLParser

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


mod("wz_bin", bin_name=lambda *a, **k: "x")
mod("bot"); mod("bot.core"); mod("bot.helper"); mod("bot.helper.ext_utils"); mod("bot.helper.telegram_helper"); mod("bot.modules")
mod("bot.helper.ext_utils.deprecations", Deprecations=type("D", (), {}))
mod("bot.core.tg_client", TgClient=types.SimpleNamespace(MAX_SPLIT_SIZE=2097152000))
cm = load("bot.core.config_manager", "bot/core/config_manager.py")
Config = cm.Config
load("bot.helper.telegram_helper.button_build", "bot/helper/telegram_helper/button_build.py")
load("bot.helper.telegram_helper.emoji", "bot/helper/telegram_helper/emoji.py")
bv = load("bot.modules.bot_settings_vars", "bot/modules/bot_settings_vars.py")
sec = load("bot.modules.bot_settings_sections", "bot/modules/bot_settings_sections.py")
from bot.helper.telegram_helper.button_build import ButtonMaker


class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.bad = []
    def handle_starttag(s, tg, a): s.stack.append(tg)
    def handle_endtag(s, tg): s.bad.append(tg) if not s.stack or s.stack.pop() != tg else None


def html_ok(t):
    p = P(); p.feed(t); return not p.bad and not p.stack


ok = True
def check(name, good):
    global ok
    ok &= bool(good); print(f"{'PASS' if good else 'FAIL'} {name}")


keys = sec.editable_keys()
placed = [k for sid in sec.SECTIONS for k in sec.section_keys(sid)]
check(f"all {len(keys)} variables in exactly one section", sorted(placed) == sorted(keys))
listed = {k for *_, ks in sec.SECTIONS.values() for k in ks}
check("section lists name only real variables", not (listed - set(Config.get_all())), )
print("   unknown:", sorted(listed - set(Config.get_all())))
check("no DISABLE_* (they stay in Module Settings)", not any(k.startswith("DISABLE_") for k in placed))

Config.BOT_TOKEN = "123456:SECRET-TOKEN-VALUE"; Config.DATABASE_URL = "mongodb+srv://u:pw-secret@x"; Config.BOT_PM = True
for prem in (False, True):
    Config.PREMIUM_EMOJI = prem
    check(f"home map html (premium={prem})", html_ok(sec.home_text()) and len(sec.home_text()) < 4096)
    for sid in sec.SECTIONS:
        all_k = sec.section_keys(sid)
        pages = max(1, -(-len(all_k) // sec.PER_PAGE))
        for page in range(1, pages + 1):
            ks, pg, pgs = sec.page_slice(all_k, page)
            t = sec.section_text(sid, ks, pg, pgs)
            good = html_ok(t) and len(t) < 4096 and "SECRET" not in t and "pw-secret" not in t
            if not good: print("   bad page", sid, page, len(t))
            ok &= good
    print(f"PASS section pages html, < 4096, no secrets (premium={prem})" if ok else "FAIL section pages")

t = sec.key_list_text(["BOT_TOKEN", "BOT_PM", "LEECH_PREFIX"])
check("states: set / ON / empty", "● set" in t and "✅ ON" in t and "○ empty" in t)
found = sec.search_keys("split")
check(f"search 'split' -> {found[:3]}", found and found[0] in ("LEECH_SPLIT_SIZE", "EQUAL_SPLITS"))
check("search 'drive' finds GDRIVE_ID", "GDRIVE_ID" in sec.search_keys("drive"))
check("search 'leech log' finds LEECH_LOG_CHAT", "LEECH_LOG_CHAT" in sec.search_keys("leech log"))
check("search nonsense -> nothing", sec.search_keys("zzqqxx") == [])
t = sec.search_text("<b>", [], 1, 1, 0)
check("search query is escaped", "&lt;b&gt;" in t and html_ok(t))

b = ButtonMaker(); sec.page_buttons(b, 5, 3, "botset sec cloud {}")
labels = [x.text for x in b.buttons["l_body"]]
check(f"page numbers {labels}", labels == ["1", "2", "•3•", "4", "5"])
longest = max(len(f"botset editvar {k}".encode()) for k in keys)
check(f"callback data <= 64 bytes (longest {longest})", longest <= 64 and all(len(f"botset sec {s} 99".encode()) <= 64 for s in sec.SECTIONS))
print("ALL PASS" if ok else "SOME FAILED")
