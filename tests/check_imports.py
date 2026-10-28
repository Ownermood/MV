"""Import every bot module with the real libraries (catches startup crashes,
circular imports, wrong names). Needs requirements.txt installed; otherwise
it is skipped. wz_bin and the MEGA SDK come from the Docker base image, so
they are stubbed here."""
import importlib, os, pkgutil, shutil, subprocess, sys, tempfile, types

REPO = sys.argv[1]
try:
    import aioqbt, pyrogram, yt_dlp  # noqa: F401
except ImportError:
    print("SKIP: requirements.txt not installed\nALL PASS")
    sys.exit(0)

work = tempfile.mkdtemp()
subprocess.run(f"git -C {REPO} archive HEAD | tar -x -C {work}", shell=True, check=True)
for name in ("bot", "sabnzbdapi", "myjd"):
    shutil.rmtree(f"{work}/{name}", ignore_errors=True)
    shutil.copytree(f"{REPO}/{name}", f"{work}/{name}")  # current files, not only HEAD
cfg = open(f"{REPO}/config_sample.py").read()
for key, value in (("BOT_TOKEN", '"1:x"'), ("OWNER_ID", "1"), ("TELEGRAM_API", "1"), ("TELEGRAM_HASH", '"x"')):
    cfg = "\n".join(f"{key} = {value}" if line.startswith(f"{key} =") else line for line in cfg.splitlines())
open(f"{work}/config.py", "w").write(cfg)
os.chdir(work)
sys.path.insert(0, work)
sys.modules["wz_bin"] = types.SimpleNamespace(bin_name=lambda name, *a, **k: name)


class _Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return _Any()
    def __call__(self, *a, **k): return _Any()


mega = types.ModuleType("mega")
mega.__getattr__ = lambda name: type(name, (_Any,), {})
sys.modules["mega"] = mega

import bot  # noqa: E402

names = ["bot.core.handlers", "bot.modules", "bot.core.startup"]
names += [m.name for m in pkgutil.walk_packages(bot.__path__, "bot.") if not m.name.endswith("__main__")]
fails = []
for name in dict.fromkeys(names):
    try:
        importlib.import_module(name)
    except Exception as e:
        fails.append(f"{name}: {type(e).__name__}: {e}")
print(f"imported {len(set(names)) - len(fails)} of {len(set(names))} modules")
for f in fails:
    print("FAIL", f)
print("SOME FAILED" if fails else "ALL PASS")
