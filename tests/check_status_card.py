"""Render the /status card with a fake task and check its HTML, length and buttons."""
import asyncio, importlib.util, sys, types
from html.parser import HTMLParser

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, f"{REPO}/{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m


class Cfg: PREMIUM_EMOJI = False; STATUS_LIMIT = 4; RICH_STATUS = True
class Lock:
    async def __aenter__(s): pass
    async def __aexit__(s, *a): pass
mod("psutil", cpu_percent=lambda: 0.2, virtual_memory=lambda: types.SimpleNamespace(percent=12.5), disk_usage=lambda p: types.SimpleNamespace(free=939 * 1024**3, percent=1.7))
mod("bot", LOGGER=types.SimpleNamespace(error=print, warning=print), DOWNLOAD_DIR="/", bot_cache={}, bot_start_time=0, status_dict={}, task_dict={}, task_dict_lock=Lock())
mod("bot.core"); mod("bot.core.config_manager", Config=Cfg); mod("bot.helper"); mod("bot.helper.ext_utils"); mod("bot.helper.telegram_helper")
mod("bot.helper.telegram_helper.bot_commands", BotCommands=types.SimpleNamespace(SelectCommand=["select", "sel"], CancelTaskCommand=["cancel", "c"]))
load("bot.helper.telegram_helper.button_build", "bot/helper/telegram_helper/button_build.py")
load("bot.helper.telegram_helper.emoji", "bot/helper/telegram_helper/emoji.py")
su = load("bot.helper.ext_utils.status_utils", "bot/helper/ext_utils/status_utils.py")
load("bot.helper.ext_utils.status_rich", "bot/helper/ext_utils/status_rich.py")


class User:
    id = 8403136097
    first_name = "OWNER & MOOD"
    def mention(self, style): return "<a href='tg://user?id=8403136097'>OWNER &amp; MOOD</a>"


class Task:
    engine = "Google-API v2.201.0"
    def __init__(self, st): self.st = st; self.listener = types.SimpleNamespace(
        subname="", progress=True, is_torrent=True, is_qbit=False, is_nzb=False, is_super_chat=True,
        mode=("#GDrive", "#Leech"), subsize=0, files_to_proceed=[], proceed_count=0,
        message=types.SimpleNamespace(from_user=User(), date=types.SimpleNamespace(timestamp=lambda: 0), link="https://t.me/c/1/2"))
    def status(self): return self.st
    def name(self): return "Compendiums <S01> & more"
    def progress(self): return "35.67%"
    def processed_bytes(self): return "42.69MB"
    def size(self): return "119.69MB"
    def speed(self): return "633.59KB/s"
    def eta(self): return "1m20s"
    def seeders_num(self): return 5
    def leechers_num(self): return 2
    def uploaded_bytes(self): return "1GB"
    def seed_speed(self): return "1MB/s"
    def ratio(self): return "0.5"
    def seeding_time(self): return "1h"
    def gid(self): return "e90c669b12"


async def tasks_for(status, uid): return TASKS
su.get_specific_tasks = tasks_for


class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.bad = []
    def handle_starttag(s, tg, a): s.stack.append(tg)
    def handle_endtag(s, tg): s.bad.append(tg) if not s.stack or s.stack.pop() != tg else None


ok = True
for prem in (False, True):
    Cfg.PREMIUM_EMOJI = prem
    for st in ("Download", "Seed", "Upload", "QueueUp"):
        TASKS = [Task(st)]
        msg, btn = asyncio.run(su.get_readable_message(1, False))
        p = P(); p.feed(msg)
        labels = [b.text for row in btn.inline_keyboard for b in row]
        good = not p.bad and not p.stack and "/c_e90c669b" in msg and "&lt;S01&gt;" in msg and ("tg-emoji" in msg) == prem and any("Refresh" in l for l in labels) and not any("Stats" in l for l in labels)
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} premium={prem!s:5} {st:9} {len(msg)} chars, buttons {labels}")
TASKS = [Task("Download") for _ in range(6)]
msg, btn = asyncio.run(su.get_readable_message(1, False))
good = len(msg) < 4096 and "Page" in msg; ok &= good
print(f"{'PASS' if good else 'FAIL'} 6 tasks paged, {len(msg)} chars")
good = su.get_progress_bar_string("35.67%") == "▰" * 4 + "▱" * 6 and len(su.get_progress_bar_string(100)) == 10
ok &= good
print(f"{'PASS' if good else 'FAIL'} progress bar {su.get_progress_bar_string('35.67%')}")
# rich version: must exist and serialize to valid TL (what is sent to Telegram)
for prem in (False, True):
    Cfg.PREMIUM_EMOJI = prem
    TASKS = [Task("Download"), Task("Upload")]
    msg, btn = asyncio.run(su.get_readable_message(1, False))
    raw_msg = msg.rich.write()
    data = raw_msg.write()
    blob = repr(raw_msg)
    good = len(data) > 200 and b"rcan e90c669b" in data and b"rsel e90c669b" in data and b"status 1 ref" in data and "PageBlockTable" not in blob and "Processed: " in blob and msg.keep_markup is False and "bg_danger=True" in blob and "bg_primary=True" in blob and ("TextCustomEmoji" in blob) == prem
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} rich card premium={prem}: {len(data)} bytes TL, cancel+select buttons, styles")
Cfg.RICH_STATUS = False
msg, _ = asyncio.run(su.get_readable_message(1, False))
good = msg.rich is None; ok &= good
print(f"{'PASS' if good else 'FAIL'} RICH_STATUS off -> no rich version")
print("ALL PASS" if ok else "SOME FAILED")
