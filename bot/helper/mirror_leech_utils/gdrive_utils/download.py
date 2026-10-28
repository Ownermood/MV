from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from io import FileIO
from json import loads as json_loads
from logging import getLogger
from os import makedirs, path as ospath, remove
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_not_exception_type,
    RetryError,
)

from ...ext_utils.bot_utils import async_to_sync
from ...ext_utils.bot_utils import SetInterval
from ...mirror_leech_utils.gdrive_utils.helper import GoogleDriveHelper

LOGGER = getLogger(__name__)


def _drop(path):
    try:
        remove(path)
    except OSError:
        pass


class DownloadBlocked(Exception):
    """The file's owner turned off downloading for viewers (cannotDownloadFile)."""


class GoogleDriveDownload(GoogleDriveHelper):
    def __init__(self, listener, path):
        self.listener = listener
        self._updater = None
        self._path = path
        super().__init__()
        self.is_downloading = True
        # names of files in a folder that the owner blocked from download
        self.skipped = []
        listener.skipped_files = self.skipped

    def download(self):
        file_id = self.get_id_from_url(self.listener.link, self.listener.user_id)
        self._updater = SetInterval(self.update_interval, self.progress)
        try:
            self.service = self.authorize()
            meta = self.get_file_metadata(file_id)
            if meta.get("mimeType") == self.G_DRIVE_DIR_MIME_TYPE:
                self._download_folder(file_id, self._path, self.listener.name)
                if self.skipped and not self._downloaded:
                    raise DownloadBlocked(
                        "The Drive owner has blocked downloads for every file in this folder."
                    )
            else:
                makedirs(self._path, exist_ok=True)
                self._download_file(
                    file_id, self._path, self.listener.name, meta.get("mimeType")
                )
        except Exception as err:
            if isinstance(err, RetryError):
                LOGGER.info(f"Total Attempts: {err.last_attempt.attempt_number}")
                err = err.last_attempt.exception()
            err = str(err).replace(">", "").replace("<", "")
            if "downloadQuotaExceeded" in err:
                err = "Download Quota Exceeded."
            elif "File not found" in err:
                if not self.alt_auth and self.use_sa:
                    self.alt_auth = True
                    self.use_sa = False
                    LOGGER.error("File not found. Trying with token.pickle...")
                    self._updater.cancel()
                    return self.download()
                err = "File not found!"
            async_to_sync(self.listener.on_download_error, err)
            self.listener.is_cancelled = True
        finally:
            self._updater.cancel()
            if self.listener.is_cancelled:
                return
            async_to_sync(self.listener.on_download_complete)
            return

    def _download_folder(self, folder_id, path, folder_name):
        folder_name = folder_name.replace("/", "")
        if not ospath.exists(f"{path}/{folder_name}"):
            makedirs(f"{path}/{folder_name}")
        path += f"/{folder_name}"
        result = self.get_files_by_folder_id(folder_id)
        if len(result) == 0:
            return
        result = sorted(result, key=lambda k: k["name"])
        for item in result:
            file_id = item["id"]
            filename = item["name"]
            shortcut_details = item.get("shortcutDetails")
            if shortcut_details is not None:
                file_id = shortcut_details["targetId"]
                mime_type = shortcut_details["targetMimeType"]
            else:
                mime_type = item.get("mimeType")
            if mime_type == self.G_DRIVE_DIR_MIME_TYPE:
                self._download_folder(file_id, path, filename)
            elif not ospath.isfile(
                f"{path}{filename}"
            ) and not filename.strip().lower().endswith(
                tuple(self.listener.excluded_extensions)
            ):
                self.sa_count = 1
                try:
                    self._download_file(file_id, path, filename, mime_type)
                    self._downloaded += 1
                except DownloadBlocked:
                    # skip only this file; the rest of the folder still downloads
                    LOGGER.info(f"Download blocked by owner, skipped: {filename}")
                    self.skipped.append(filename)
            if self.listener.is_cancelled:
                break

    _downloaded = 0

    @retry(
        wait=wait_exponential(multiplier=2, min=3, max=6),
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type(DownloadBlocked),
    )
    def _download_file(self, file_id, path, filename, mime_type, export=False):
        if export:
            request = self.service.files().export_media(
                fileId=file_id, mimeType="application/pdf"
            )
        else:
            request = self.service.files().get_media(
                fileId=file_id, supportsAllDrives=True, acknowledgeAbuse=True
            )
        filename = filename.replace("/", "")
        if export:
            filename = f"{filename}.pdf"
        if len(filename.encode()) > 255:
            ext = ospath.splitext(filename)[1]
            filename = f"{filename[:245]}{ext}"

            if self.listener.name.strip().endswith(ext):
                self.listener.name = filename
        if self.listener.is_cancelled:
            return
        fh = FileIO(f"{path}/{filename}", "wb")
        downloader = MediaIoBaseDownload(fh, request, chunksize=100 * 1024 * 1024)
        done = False
        retries = 0
        while not done:
            if self.listener.is_cancelled:
                fh.close()
                break
            try:
                self.status, done = downloader.next_chunk()
            except HttpError as err:
                LOGGER.error(err)
                if err.resp.status in [500, 502, 503, 504, 429] and retries < 10:
                    retries += 1
                    continue
                if err.resp.get("content-type", "").startswith("application/json"):
                    reason = (
                        json_loads(err.content)
                        .get("error")
                        .get("errors")[0]
                        .get("reason")
                    )
                    if export:
                        # a Google file that cannot be exported either (Forms, too big)
                        fh.close()
                        _drop(fh.name)
                        self.proc_bytes -= self.file_processed_bytes
                        self.file_processed_bytes = 0
                        self.status = None
                        raise DownloadBlocked(f"Google file could not be exported ({reason}).")
                    if reason == "cannotDownloadFile":
                        fh.close()
                        _drop(fh.name)
                        self.proc_bytes -= self.file_processed_bytes
                        self.file_processed_bytes = 0
                        self.status = None
                        raise DownloadBlocked(
                            "The Drive owner has blocked downloads for this file."
                        )
                    # Docs, Sheets, Slides, Drawings: download them as PDF
                    if "fileNotDownloadable" in reason and (
                        "document" in mime_type
                        or mime_type.startswith("application/vnd.google-apps.")
                    ):
                        fh.close()
                        _drop(fh.name)  # the empty original; the PDF replaces it
                        self.proc_bytes -= self.file_processed_bytes
                        self.file_processed_bytes = 0
                        self.status = None
                        return self._download_file(
                            file_id, path, filename, mime_type, True
                        )
                    if reason not in [
                        "downloadQuotaExceeded",
                        "dailyLimitExceeded",
                    ]:
                        raise err
                    if self.use_sa:
                        if self.sa_count >= self.sa_number:
                            LOGGER.info(
                                f"Reached maximum number of service accounts switching, which is {self.sa_count}"
                            )
                            raise err
                        else:
                            if self.listener.is_cancelled:
                                return
                            self.switch_service_account()
                            LOGGER.info(f"Got: {reason}, Trying Again...")
                            fh.close()
                            self.proc_bytes -= self.file_processed_bytes
                            self.file_processed_bytes = 0
                            self.status = None
                            return self._download_file(
                                file_id, path, filename, mime_type
                            )
                    else:
                        LOGGER.error(f"Got: {reason}")
                        raise err
        self.file_processed_bytes = 0
