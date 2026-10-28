"""Faster Google Drive downloads.

A big file is fetched in pieces over several connections at once (HTTP Range),
and the small files of a folder are fetched several at a time. Anything that
goes wrong raises FastFailed, and the caller falls back to the normal
one-connection download, which has all the Drive error handling (blocked
files, quota, service account switching, Docs export)."""

from concurrent.futures import ThreadPoolExecutor
from os import O_CREAT, O_TRUNC, O_WRONLY, close, ftruncate, open as os_open, pwrite
from threading import Event, Lock, local

from google.auth.transport.requests import AuthorizedSession, Request

API = (
    "https://www.googleapis.com/drive/v3/files/{}"
    "?alt=media&supportsAllDrives=true&acknowledgeAbuse=true"
)
PIECE = 32 * 1024 * 1024
CONNECTIONS = 8  # pieces of one big file at once
PARALLEL_FILES = 6  # small files of a folder at once
BIG = 64 * 1024 * 1024  # files at least this big are split into pieces
TIMEOUT = (15, 60)


class FastFailed(Exception):
    pass


class Counter:
    """Looks like MediaIoBaseDownload's status, so helper.progress() can read
    it: total_size * progress() is the number of bytes done."""

    total_size = 1

    def __init__(self):
        self.bytes = 0
        self._lock = Lock()

    def add(self, n):
        with self._lock:
            self.bytes += n

    def progress(self):
        return self.bytes


def _fresh(credentials):
    if not credentials.valid:
        credentials.refresh(Request())


def _sessions(credentials):
    store = local()

    def get():
        if not hasattr(store, "session"):
            store.session = AuthorizedSession(credentials)
        return store.session

    return get


def _fetch(session, file_id, fd, counter, stop, start=0, end=None):
    headers = {"Range": f"bytes={start}-{end}"} if end is not None else {}
    with session.get(
        API.format(file_id), headers=headers, stream=True, timeout=TIMEOUT
    ) as resp:
        if resp.status_code not in (200, 206):
            raise FastFailed(f"HTTP {resp.status_code}")
        if end is not None and resp.status_code != 206:
            raise FastFailed("Drive ignored the byte range")
        pos = start
        for chunk in resp.iter_content(1024 * 1024):
            if stop.is_set():
                raise FastFailed("stopped")
            pwrite(fd, chunk, pos)
            pos += len(chunk)
            counter.add(len(chunk))
    if end is not None and pos != end + 1:
        raise FastFailed("connection closed early")


def _run(jobs, workers, stop):
    def guard(job):
        if stop.is_set():
            raise FastFailed("stopped")
        try:
            return job()
        except BaseException:
            stop.set()  # the other pieces stop at their next chunk
            raise

    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(guard, job) for job in jobs]
    for future in futures:
        future.result()


def download_big(credentials, file_id, out_path, size, counter, cancelled):
    """One file, CONNECTIONS pieces at once."""
    _fresh(credentials)
    session = _sessions(credentials)
    stop = Event()
    fd = os_open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0o644)
    try:
        ftruncate(fd, size)

        def piece(start):
            if cancelled():
                stop.set()
                raise FastFailed("cancelled")
            end = min(start + PIECE, size) - 1
            _fetch(session(), file_id, fd, counter, stop, start, end)

        _run([lambda s=s: piece(s) for s in range(0, size, PIECE)], CONNECTIONS, stop)
    finally:
        close(fd)


def download_many(credentials, files, counter, cancelled):
    """Small files, PARALLEL_FILES at once. files: (file_id, out_path).
    Returns the files that failed, for the normal download to retry."""
    _fresh(credentials)
    session = _sessions(credentials)
    failed = []
    lock = Lock()
    never = Event()  # one small file failing does not stop the others

    def one(file_id, out_path):
        if cancelled():
            return
        done = Counter()
        try:
            fd = os_open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0o644)
            try:
                _fetch(session(), file_id, fd, done, never)
            finally:
                close(fd)
            counter.add(done.bytes)
        except Exception:
            with lock:
                failed.append((file_id, out_path))

    with ThreadPoolExecutor(PARALLEL_FILES) as pool:
        list(pool.map(lambda f: one(*f), files))
    return failed
