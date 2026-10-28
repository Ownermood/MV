"""Fast Drive downloads against a local fake Drive server: a big file comes in
pieces over several connections and matches byte for byte; small files of a
folder come several at once; anything the fast way cannot do (no byte ranges,
403, a connection cut) falls back to the normal download."""
import hashlib, importlib.util, os, sys, tempfile, threading, time, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google.oauth2.credentials import Credentials

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


BLOBS = {k: os.urandom(n) for k, n in {"big": 3_000_000, "norange": 2_000_000, "cut": 2_500_000,
                                         **{f"s{i}": 10_000 + i for i in range(8)}, "x": 5000}.items()}
hits = {"auth": set(), "ranges": 0, "max_parallel": 0}
active = [0]
lock = threading.Lock()


class Drive(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        fid = self.path.split("/")[-1].split("?")[0]
        hits["auth"].add(self.headers.get("Authorization"))
        with lock:
            active[0] += 1; hits["max_parallel"] = max(hits["max_parallel"], active[0])
        try:
            if fid == "x":
                self.send_response(403); self.end_headers(); return
            data = BLOBS[fid]
            time.sleep(0.05)  # like a real network, so parallel requests overlap
            rng = self.headers.get("Range")
            if rng and fid != "norange":
                start, end = map(int, rng.split("=")[1].split("-"))
                hits["ranges"] += 1
                body = data[start:end + 1]
                self.send_response(206)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if fid == "cut" and start > 0:
                    self.wfile.write(body[: len(body) // 2]); return  # connection cut short
                self.wfile.write(body)
            else:
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        finally:
            with lock:
                active[0] -= 1


ThreadingHTTPServer.handle_error = lambda *a: None  # client hung up on purpose
server = ThreadingHTTPServer(("127.0.0.1", 0), Drive)
threading.Thread(target=server.serve_forever, daemon=True).start()

old_calls = []


class Helper:
    G_DRIVE_DIR_MIME_TYPE = "application/vnd.google-apps.folder"
    update_interval = 99
    alt_auth = use_sa = False
    sa_count = sa_number = 1

    def __init__(self):
        self.file_processed_bytes = self.proc_bytes = 0
        self.status = None

    def get_id_from_url(self, link, uid): return link
    def authorize(self): return Service()
    def get_file_metadata(self, fid): return META[fid]
    def get_files_by_folder_id(self, fid): return META[fid]["items"]
    def progress(self): pass


class Interval:
    def __init__(self, *a): pass
    def cancel(self): pass


mod("bot"); mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.bot_utils", async_to_sync=lambda fn, *a: fn(*a), SetInterval=Interval)
mod("bot.helper.mirror_leech_utils")
mod("bot.helper.mirror_leech_utils.gdrive_utils").__path__ = [f"{REPO}/bot/helper/mirror_leech_utils/gdrive_utils"]
mod("bot.helper.mirror_leech_utils.gdrive_utils.helper", GoogleDriveHelper=Helper)
spec = importlib.util.spec_from_file_location("bot.helper.mirror_leech_utils.gdrive_utils.download",
                                              f"{REPO}/bot/helper/mirror_leech_utils/gdrive_utils/download.py")
dl = importlib.util.module_from_spec(spec); sys.modules[spec.name] = dl; spec.loader.exec_module(dl)
fast = sys.modules["bot.helper.mirror_leech_utils.gdrive_utils.fast_download"]
fast.API = f"http://127.0.0.1:{server.server_port}/files/{{}}?alt=media"
fast.PIECE = 256 * 1024
dl.BIG = fast.BIG = 1_000_000
dl.GoogleDriveDownload._download_file.retry.wait = lambda *a, **k: 0


class Downloader:
    """The normal one-connection download (stub): writes the real bytes."""
    def __init__(self, fh, request, chunksize): self.fh, self.fid = fh, request
    def next_chunk(self):
        old_calls.append(self.fid)
        if self.fid == "x":
            from googleapiclient.errors import HttpError
            class R(dict): status = 403; reason = "Forbidden"
            raise HttpError(R({"content-type": "application/json"}), b'{"error":{"errors":[{"reason":"cannotDownloadFile"}]}}')
        self.fh.write(BLOBS[self.fid]); return None, True


dl.MediaIoBaseDownload = Downloader


class Service:
    _http = types.SimpleNamespace(credentials=Credentials(token="tok123"))
    def files(self): return self
    def get_media(self, fileId, **k): return fileId


def item(fid): return {"id": fid, "name": f"{fid}.bin", "mimeType": "video/mp4", "size": str(len(BLOBS[fid]))}


META = {
    "big": {"mimeType": "video/mp4", "size": str(len(BLOBS["big"]))},
    "dir": {"mimeType": Helper.G_DRIVE_DIR_MIME_TYPE,
            "items": [item(k) for k in ("big", "norange", "cut", "x")] + [item(f"s{i}") for i in range(8)]},
}


class Listener:
    def __init__(self, link, name):
        self.link, self.name, self.user_id, self.is_cancelled = link, name, 1, False
        self.excluded_extensions, self.done, self.errors = [], False, []
    def on_download_error(self, err): self.errors.append(err)
    def on_download_complete(self): self.done = True


ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)


md5 = lambda b: hashlib.md5(b).hexdigest()
with tempfile.TemporaryDirectory() as work:
    lst = Listener("big", "big.mkv")
    d = dl.GoogleDriveDownload(lst, work); d.download()
    got = open(f"{work}/big.mkv", "rb").read()
    t("big file: pieces over several connections, identical bytes", lst.done and md5(got) == md5(BLOBS["big"]) and hits["ranges"] >= 12)
    t(f"several connections at once (max {hits['max_parallel']})", hits["max_parallel"] >= 4)
    t("progress counts every byte once", d.proc_bytes == len(BLOBS["big"]) and d.status is None)
    t("token sent to Drive", hits["auth"] == {"Bearer tok123"})
    t("normal download not used", old_calls == [])

with tempfile.TemporaryDirectory() as work:
    old_calls.clear(); hits["max_parallel"] = 0
    lst = Listener("dir", "F")
    d = dl.GoogleDriveDownload(lst, work); d.download()
    good = all(open(f"{work}/F/{k}.bin", "rb").read() == BLOBS[k] for k in ["big", "norange", "cut"] + [f"s{i}" for i in range(8)])
    t("folder: every file correct (fast, and fallbacks)", lst.done and good and not lst.errors)
    t(f"no byte ranges / cut connection -> normal download {sorted(old_calls)}", sorted(old_calls) == ["cut", "norange", "x"])
    t("403 small file -> normal download -> skipped as blocked", lst.skipped_files == ["x.bin"] and not os.path.exists(f"{work}/F/x.bin"))
    t(f"small files several at once (max {hits['max_parallel']})", hits["max_parallel"] >= 3)
    fast_bytes = len(BLOBS["big"]) + sum(len(BLOBS[f"s{i}"]) for i in range(8))
    t(f"progress = bytes of fast files ({d.proc_bytes} == {fast_bytes})", d.proc_bytes == fast_bytes)

with tempfile.TemporaryDirectory() as work:
    old_calls.clear()
    lst = Listener("big", "big.mkv"); lst.is_cancelled = True
    d = dl.GoogleDriveDownload(lst, work); d._path = work
    d.service = Service()
    d._download_file("big", work, "big.mkv", "video/mp4", size=len(BLOBS["big"]))
    t("cancelled task: nothing downloaded", old_calls == [] and not os.path.exists(f"{work}/big.mkv"))
server.shutdown()
print("ALL PASS" if ok else "SOME FAILED")
