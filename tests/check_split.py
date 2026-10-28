"""Split a real test video with FFMpeg.split: the part count must match the plan,
every part must fit the size limit and no video time may be lost.
Needs ffmpeg/ffprobe (and taskset) on PATH."""
import ast, asyncio, json, os, subprocess, sys, types
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from contextlib import suppress
from os import path as ospath

REPO, WORK = sys.argv[1], sys.argv[2]
src = open(f"{REPO}/bot/helper/ext_utils/media_utils.py").read()
cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "FFMpeg")
fn = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "split")


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", p], capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


async def get_media_info(p):
    return (round(probe(p)), None, None)


class aiopath:
    @staticmethod
    async def getsize(p): return os.path.getsize(p)


async def remove(p): os.remove(p)

ns = {"ffmpeg_layout": lambda: ("0", 1), "BinConfig": types.SimpleNamespace(FFMPEG_NAME="ffmpeg"),
      "get_media_info": get_media_info, "ospath": ospath, "create_subprocess_exec": create_subprocess_exec,
      "PIPE": PIPE, "suppress": suppress, "remove": remove, "aiopath": aiopath,
      "LOGGER": types.SimpleNamespace(warning=print, error=print, info=print)}
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), "split", "exec"), ns)


class FF:
    split = ns["split"]
    def __init__(s, listener): s._listener = listener; s._last_processed_time = 0; s._last_processed_bytes = 0
    def clear(s): pass
    async def _ffmpeg_progress(s): pass


os.makedirs(WORK, exist_ok=True)
video = os.path.join(WORK, "movie.mkv")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=25", "-f", "lavfi", "-i",
                "sine=frequency=440", "-t", "60", "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "8M", "-minrate", "8M", "-maxrate", "8M", "-bufsize", "8M", "-x264-params", "nal-hrd=cbr", "-g", "50",
                "-c:a", "aac", video], check=True)
size, total = os.path.getsize(video), probe(video)
ok = True
for split_size in (int(size * 0.6), int(size * 0.4)):
    for f in os.listdir(WORK):
        if ".part" in f: os.remove(os.path.join(WORK, f))
    parts = -(-size // split_size)
    lst = types.SimpleNamespace(split_size=split_size, max_split_size=split_size, is_cancelled=False, subproc=None)
    equal = (size // parts) + (size % parts)
    asyncio.run(FF(lst).split(video, "movie.mkv", parts, equal))
    made = sorted(f for f in os.listdir(WORK) if ".part" in f)
    sizes = [os.path.getsize(os.path.join(WORK, f)) for f in made]
    durs = [probe(os.path.join(WORK, f)) for f in made]
    good = len(made) == parts and max(sizes) <= split_size and sum(durs) >= total - 0.5
    ok &= good
    print(f"{'PASS' if good else 'FAIL'} {size // 10**6}MB, limit {split_size // 10**6}MB -> {parts} parts planned, "
          f"{len(made)} made, sizes {[s // 10**6 for s in sizes]}MB, durations {[round(d, 1) for d in durs]}s of {round(total, 1)}s")
print("ALL PASS" if ok else "SOME FAILED")
