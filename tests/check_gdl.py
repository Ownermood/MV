import sys, types, importlib.util, asyncio, threading, os, http.server, functools, struct, zlib
REPO, WORK = sys.argv[1], sys.argv[2]
# --- stub the bot package pieces the downloader imports ---
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
loop = asyncio.new_event_loop()
async def sync_to_async(f, *a, **k): return await loop.run_in_executor(None, functools.partial(f, *a, **k))
def async_to_sync(f, *a, **k): return asyncio.run_coroutine_threadsafe(f(*a, **k), loop).result()
async def ok_check(listener, *a): return (None, None)
async def no_queue(listener): return (False, None)
async def no_limit(listener, *a): return None
async def noop(*a, **k): return None
mod("bot", task_dict={}, task_dict_lock=asyncio.Lock())
mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.bot_utils", sync_to_async=sync_to_async, async_to_sync=async_to_sync)
mod("bot.helper.ext_utils.task_manager", check_running_tasks=no_queue, stop_duplicate_check=ok_check, limit_checker=no_limit)
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.status_utils")
mod("bot.helper.mirror_leech_utils.status_utils.queue_status", QueueStatus=object)
mod("bot.helper.mirror_leech_utils.status_utils.gallery_dl_status", GalleryDLStatus=lambda *a: "status")
mod("bot.helper.telegram_helper"); mod("bot.helper.telegram_helper.message_utils", send_status_message=noop)
mod("bot.helper.mirror_leech_utils.download_utils")
mod("bot.helper.mirror_leech_utils.download_utils.yt_dlp_download", get_cookie_file=lambda d: "nonexistent-cookies.txt")
name = "bot.helper.mirror_leech_utils.download_utils.gallery_dl_download"
spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/helper/mirror_leech_utils/download_utils/gallery_dl_download.py")
g = importlib.util.module_from_spec(spec); sys.modules[name] = g; spec.loader.exec_module(g)

ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)

# --- sanitizer ---
san = g.sanitize_gallery_dl_options
t("benign kept", san({"image-range": "1-5", "extractor": {"pixiv": {"username": "u"}}}) == {"image-range": "1-5", "extractor": {"pixiv": {"username": "u"}}})
t("postprocessors dropped (top + nested)", san({"postprocessors": [{"name": "exec", "command": "id"}], "extractor": {"x": {"postprocessors": [{"name": "python"}]}}}) == {"extractor": {"x": {}}})
t("config-files/archive/base-directory/output dropped", san({"config-files": ["a"], "archive": "a.db", "base-directory": "x", "output": {"logfile": "x"}}) == {})
t("cookies path dropped, dict kept", san({"cookies": "/etc/x", "extractor": {"tw": {"cookies": {"a": "b"}}}}) == {"extractor": {"tw": {"cookies": {"a": "b"}}}})
t("abs/traversal values dropped", san({"directory": ["..", "x"], "filename": "/tmp/{id}", "proxy": "http://p:1"}) == {"directory": ["x"], "proxy": "http://p:1"})
t("ytdl raw-options/module dropped", san({"extractor": {"ytdl": {"module": "os", "raw-options": {"exec": "id"}}}}) == {"extractor": {"ytdl": {}}})
t("non-dict -> {}", san("x") == {})

# --- real download through gallery-dl's directlink extractor ---
www = f"{WORK}/www"
def png():
    raw = b"\x00\xff\x00\x00"
    def chunk(tag, data): return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
open(f"{www}/cat.png", "wb").write(png())
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=www))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/cat.png"
from gallery_dl import extractor
t("directlink extractor matches url", extractor.find(url) is not None)

class Listener:
    def __init__(self, link):
        self.link, self.name, self.size, self.mid, self.multi, self.is_rss = link, "", 0, 1, 0, False
        self.is_cancelled, self.user_dict, self.message = False, {}, None
        self.done = asyncio.Event(); self.error = None
    async def on_download_start(self): pass
    async def on_download_complete(self): self.done.set()
    async def on_download_error(self, e, button=None, is_limit=False): self.error = e; self.done.set()

async def run():
    dl = f"{WORK}/dl/1"
    L = Listener(url)
    await g.GalleryDLHelper(L).add_download(dl, san({"image-range": "1", "postprocessors": [{"name": "exec", "command": "touch PWNED"}]}))
    files = [os.path.join(r, f) for r, _, fs in os.walk(dl) for f in fs]
    t(f"download completed (error={L.error})", L.done.is_set() and L.error is None)
    t(f"file saved inside task dir: {files}", len(files) == 1 and files[0].endswith(".png") and files[0].startswith(dl))
    t(f"listener.size set ({L.size})", L.size == len(png()))
    t(f"listener.name set ({L.name})", bool(L.name))
    t("exec postprocessor did not run", not os.path.exists("PWNED") and not os.path.exists(f"{dl}/PWNED"))
    L2 = Listener(f"http://127.0.0.1:{srv.server_port}/missing.png")
    await g.GalleryDLHelper(L2).add_download(f"{WORK}/dl/2", {})
    t(f"404 reported as error ({str(L2.error)[:60]!r})", L2.error is not None)
async def run_parallel():
    open(f"{www}/dog.png", "wb").write(png())
    La, Lb = Listener(url), Listener(f"http://127.0.0.1:{srv.server_port}/dog.png")
    da, db = f"{WORK}/dl/a", f"{WORK}/dl/b"
    await asyncio.gather(g.GalleryDLHelper(La).add_download(da, {}), g.GalleryDLHelper(Lb).add_download(db, {}))
    fa = [f for _, _, fs in os.walk(da) for f in fs]; fb = [f for _, _, fs in os.walk(db) for f in fs]
    t(f"parallel: each file in own task dir a={fa} b={fb}", fa and fb and all("cat" in f for f in fa) and all("dog" in f for f in fb))
loop.run_until_complete(run())
loop.run_until_complete(run_parallel())
srv.shutdown()
print("ALL PASS" if ok else "SOME FAILED")
