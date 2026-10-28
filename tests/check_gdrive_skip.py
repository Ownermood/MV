"""Drive folder download: a file whose owner blocked downloads is skipped (no
retries) and the rest of the folder still downloads; a folder where every file
is blocked, or a single blocked file, stops with a clear reason."""
import importlib.util, json, os, sys, tempfile, types

from googleapiclient.errors import HttpError

REPO = sys.argv[1]


def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m


errors = []


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
    def get_file_metadata(self, fid): return {"mimeType": FILES[fid]["mime"]}
    def get_files_by_folder_id(self, fid): return FILES[fid]["items"]
    def progress(self): pass


class Interval:
    def __init__(self, *a): pass
    def cancel(self): pass


def async_to_sync(fn, *a): return fn(*a)


mod("bot"); mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.bot_utils", async_to_sync=async_to_sync, SetInterval=Interval)
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.gdrive_utils")
mod("bot.helper.mirror_leech_utils.gdrive_utils.helper", GoogleDriveHelper=Helper)
spec = importlib.util.spec_from_file_location(
    "bot.helper.mirror_leech_utils.gdrive_utils.download",
    f"{REPO}/bot/helper/mirror_leech_utils/gdrive_utils/download.py",
)
dl = importlib.util.module_from_spec(spec); sys.modules[spec.name] = dl; spec.loader.exec_module(dl)
dl.GoogleDriveDownload._download_file.retry.wait = lambda *a, **k: 0

calls = []


class Resp(dict):
    status = 403
    reason = "Forbidden"


def blocked(reason="cannotDownloadFile"):
    body = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()
    return HttpError(Resp({"content-type": "application/json"}), body)


class Downloader:
    def __init__(self, fh, request, chunksize): self.fh, self.fid = fh, request

    def next_chunk(self):
        calls.append(self.fid)
        if isinstance(self.fid, tuple):  # export to PDF
            if not FILES[self.fid[1]].get("exportable"):
                raise blocked("exportFormatNotSupported")
        elif FILES[self.fid].get("gfile"):
            raise blocked("fileNotDownloadable")
        elif FILES[self.fid].get("blocked"):
            raise blocked()
        self.fh.write(b"data")
        return None, True


dl.MediaIoBaseDownload = Downloader


class Service:
    def files(self): return self
    def get_media(self, fileId, **k): return fileId
    def export_media(self, fileId, mimeType): return ("export", fileId)


def item(fid, name): return {"id": fid, "name": name, "mimeType": "video/mp4"}


FILES = {
    "dir": {"mime": Helper.G_DRIVE_DIR_MIME_TYPE, "items": [item("a", "1.mp4"), item("b", "2.mp4"), item("c", "3.mp4")]},
    "a": {}, "b": {"blocked": True}, "c": {},
    "alldir": {"mime": Helper.G_DRIVE_DIR_MIME_TYPE, "items": [item("b", "2.mp4")]},
    "one": {"mime": "video/mp4", "blocked": True},
    "gdir": {"mime": Helper.G_DRIVE_DIR_MIME_TYPE, "items": [
        {"id": "s", "name": "Marks", "mimeType": "application/vnd.google-apps.spreadsheet"},
        {"id": "f", "name": "Quiz", "mimeType": "application/vnd.google-apps.form"},
        item("a", "1.mp4")]},
    "s": {"gfile": True, "exportable": True}, "f": {"gfile": True},
}


class Listener:
    def __init__(self, link):
        self.link, self.user_id, self.name, self.is_cancelled = link, 1, "Folder", False
        self.excluded_extensions, self.done = [], False
    def on_download_error(self, err): errors.append(err)
    def on_download_complete(self): self.done = True


ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)


with tempfile.TemporaryDirectory() as work:
    lst = Listener("dir"); calls.clear()
    dl.GoogleDriveDownload(lst, work).download()
    files = sorted(os.listdir(f"{work}/Folder"))
    t(f"other files downloaded {files}", files == ["1.mp4", "3.mp4"] and lst.done and not errors)
    t("blocked file listed as skipped", lst.skipped_files == ["2.mp4"])
    t(f"blocked file not retried (calls {calls})", calls.count("b") == 1)

    lst = Listener("alldir"); lst.name = "All"
    dl.GoogleDriveDownload(lst, work).download()
    t("all files blocked -> clear error", not lst.done and errors and "every file" in errors[-1])

    lst = Listener("one"); lst.name = "one.mp4"; errors.clear()
    dl.GoogleDriveDownload(lst, work).download()
    t("single blocked file -> clear error", not lst.done and errors and "blocked downloads for this file" in errors[-1])
with tempfile.TemporaryDirectory() as work:
    lst = Listener("gdir"); lst.name = "G"; errors.clear()
    dl.GoogleDriveDownload(lst, work).download()
    files = sorted(os.listdir(f"{work}/G"))
    t(f"Google Sheet exported as PDF, Form skipped, task goes on {files}", files == ["1.mp4", "Marks.pdf"] and lst.done and not errors)
    t("unexportable Google file listed as skipped", lst.skipped_files == ["Quiz"])
print("ALL PASS" if ok else "SOME FAILED")
