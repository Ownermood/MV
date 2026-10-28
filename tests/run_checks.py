"""Run the security/port checks: python3 tests/run_checks.py

They load single functions or modules from the bot with stubs, so no
Telegram config is needed. Extra packages: pip install -r tests/requirements.txt
check_tldv and check_split also need ffmpeg/ffprobe on PATH.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
T = REPO / "tests"
B = REPO / "bot"


def tldv_setup(work):
    seg = ["ffmpeg", "-loglevel", "error"]
    subprocess.run(seg + ["-f", "lavfi", "-i", "testsrc=duration=3:size=160x120:rate=10", "-c:v", "libx264", "-g", "10", "-f", "mpegts", "-y", f"{work}/full.ts"], check=True)
    subprocess.run(seg + ["-i", f"{work}/full.ts", "-c", "copy", "-f", "segment", "-segment_time", "1", "-segment_format", "mpegts", f"{work}/seg%d.ts"], check=True)


def gdl_setup(work):
    Path(work, "www").mkdir()
    Path(work, "dl").mkdir()


CHECKS = [
    ("yt-dlp option sanitizer", "check_sanitize.py", [B / "modules/ytdlp.py"], None),
    ("ffmpeg cmd validator", "check_ff.py", [B / "helper/ext_utils/media_utils.py"], None),
    ("token.pickle unpickler", "check_pickle.py", [B / "helper/mirror_leech_utils/gdrive_utils/helper.py"], None),
    ("rclone flags/config", "check_rclone.py", [B / "helper/mirror_leech_utils/rclone_utils/transfer.py"], None),
    ("extracted symlinks", "check_links.py", [REPO, "WORK"], None),
    ("gallery-dl downloader", "check_gdl.py", [REPO, "WORK"], gdl_setup),
    ("TorBox resolver", "check_torbox.py", [REPO], None),
    ("tl;dv downloader", "check_tldv.py", [REPO, "WORK"], tldv_setup),
    ("rclone file manager", "check_rcfm.py", [REPO, "WORK"], None),
    ("debrid resolve /cancel", "check_resolve_cancel.py", [REPO], None),
    ("broadcast loop", "check_broadcast.py", [REPO], None),
    ("/start + guide pages", "check_start_menu.py", [REPO], None),
    ("admin panel", "check_admin_panel.py", [REPO], None),
    ("force join", "check_force_join.py", [REPO], None),
    ("force join auto-verify", "check_auto_verify.py", [REPO], None),
    ("status card", "check_status_card.py", [REPO], None),
    ("video split into parts", "check_split.py", [REPO, "WORK"], None),
    ("bot settings sections", "check_bsettings_sections.py", [REPO], None),
    ("drive: skip blocked files", "check_gdrive_skip.py", [REPO], None),
    ("leech sections", "check_sections.py", [REPO], None),
    ("task error routing", "check_error_report.py", [REPO], None),
]

failed = []
for name, script, args, setup in CHECKS:
    with tempfile.TemporaryDirectory() as tmp:
        work = str(Path(tmp, "w"))
        Path(work).mkdir()
        if setup:
            setup(work)
        argv = [str(a) if a != "WORK" else work for a in args]
        res = subprocess.run([sys.executable, "-I", str(T / script), *argv], capture_output=True, text=True, cwd=work)
        out = res.stdout + res.stderr
        passed = "ALL PASS" in out and res.returncode == 0
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
        if not passed:
            failed.append(name)
            print("\n".join("    " + line for line in out.strip().splitlines()[-15:]))
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
sys.exit(1 if failed else 0)
