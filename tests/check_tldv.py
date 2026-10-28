import sys, types, importlib.util, asyncio, logging, os, json, subprocess
REPO, WORK = sys.argv[1], sys.argv[2]
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
async def cmd_exec(cmd, shell=False):
    p = subprocess.run(cmd, capture_output=True, text=True); return p.stdout, p.stderr, p.returncode
async def no_queue(listener): return (False, None)
async def noop(*a, **k): return None
mod("bot", LOGGER=logging.getLogger("t"), task_dict={}, task_dict_lock=asyncio.Lock()); mod("bot.core")
mod("bot.core.config_manager", Config=type("C", (), {"TLDV_TOKEN": "OWNER_TOKEN"}), BinConfig=type("B", (), {"FFMPEG_NAME": "ffmpeg"}))
mod("bot.helper"); mod("bot.helper.ext_utils"); mod("bot.helper.ext_utils.bot_utils", cmd_exec=cmd_exec)
mod("bot.helper.ext_utils.task_manager", check_running_tasks=no_queue)
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.status_utils")
mod("bot.helper.mirror_leech_utils.status_utils.queue_status", QueueStatus=object)
mod("bot.helper.mirror_leech_utils.status_utils.tldv_status", TldvStatus=lambda *a: "status")
mod("bot.helper.telegram_helper"); mod("bot.helper.telegram_helper.message_utils", send_status_message=noop)
mod("bot.helper.mirror_leech_utils.download_utils")
name = "bot.helper.mirror_leech_utils.download_utils.tldv_downloader"
spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/helper/mirror_leech_utils/download_utils/tldv_downloader.py")
tl = importlib.util.module_from_spec(spec); sys.modules[name] = tl; spec.loader.exec_module(tl)
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
t("token from -h bearer", tl.get_tldv_token("authorization: Bearer abc.DEF-1 referer: x") == "abc.DEF-1")
t("token from -h cookie", tl.get_tldv_token("cookie: a=1; tldvToken=zzz9; b=2") == "zzz9")
t("token falls back to config", tl.get_tldv_token("") == "OWNER_TOKEN")
t("tldv host check", tl._is_tldv_host("https://gaia.tldv.io/x") and not tl._is_tldv_host("https://cdn.evil.com/x") and not tl._is_tldv_host("https://tldv.io.evil.com/x"))
t("caesar roundtrip", tl.caesar_decipher(tl.caesar_decipher("Seg01.ts", 5), -5) == "Seg01.ts")
segs = sorted(f for f in os.listdir(WORK) if f.startswith("seg"))
offset = 7
enc = [tl.caesar_decipher(s, -offset) for s in segs]
playlist = "#EXTM3U\n#TLDVCONF:999,%d,https://cdn.example.net/m/\n" % offset + "\n".join("#EXTINF:1,\n" + e for e in enc)
seen = []
class R:
    def __init__(self, code, body): self.status_code = code; self.content = body if isinstance(body, bytes) else body.encode(); self.text = self.content.decode(errors="ignore")
    def json(self): return json.loads(self.text)
class FakeSession:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): pass
    async def get(self, url, headers=None, timeout=None):
        seen.append((url, (headers or {}).get("Authorization")))
        if "watch-page" in url: return R(200, json.dumps({"meeting": {"name": "Weekly Sync / Q3?", "createdAt": "2026-10-01T10:00:00Z"}}))
        if url.endswith("playlist.m3u8"): return R(200, playlist)
        if url.startswith("https://cdn.example.net/m/"):
            return R(200, open(os.path.join(WORK, url.rsplit("/", 1)[1]), "rb").read())
        return R(404, "")
tl.AsyncSession = FakeSession
class Listener:
    def __init__(self):
        self.link = "https://tldv.io/app/meetings/abc123"; self.name = ""; self.size = 0; self.mid = 1; self.multi = 0
        self.is_rss = False; self.is_cancelled = False; self.message = None; self.error = None; self.done = False
    async def on_download_start(self): pass
    async def on_download_complete(self): self.done = True
    async def on_download_error(self, e, *a, **k): self.error = e
async def main():
    out = os.path.join(WORK, "out"); os.makedirs(out, exist_ok=True)
    L = Listener()
    await tl.add_tldv_download(L, out, "")
    t(f"download completed (error={L.error})", L.done and L.error is None)
    t(f"name sanitized: {L.name}", L.name == "2026-10-01_Weekly_Sync__Q3.mp4")
    mp4 = os.path.join(out, L.name)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4], capture_output=True, text=True).stdout.strip()
    t(f"mp4 playable, duration={probe}s", probe and abs(float(probe) - 3.0) < 0.5)
    t(f"temp files cleaned {sorted(os.listdir(out))}", sorted(os.listdir(out)) == [L.name])
    t("listener.size = file size", L.size == os.path.getsize(mp4))
    tldv_auth = [a for u, a in seen if ".tldv.io" in u]; cdn_auth = [a for u, a in seen if "cdn.example.net" in u]
    t("token sent to tldv hosts", tldv_auth and all(a == "Bearer OWNER_TOKEN" for a in tldv_auth))
    t(f"token NOT sent to segment CDN ({len(cdn_auth)} reqs)", cdn_auth and all(a is None for a in cdn_auth))
    async def g403(self, url, headers=None, timeout=None): return R(403, "")
    FakeSession.get = g403
    L2 = Listener()
    await tl.add_tldv_download(L2, os.path.join(WORK, "out2"), "")
    t(f"auth error surfaced: {L2.error}", L2.error and "Authentication required" in L2.error)
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
