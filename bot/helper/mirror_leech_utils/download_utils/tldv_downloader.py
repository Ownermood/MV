from asyncio import Semaphore, gather, sleep
from os import path as ospath
from re import IGNORECASE, match as re_match, search as re_search, sub as re_sub
from secrets import token_hex
from time import time
from urllib.parse import urlparse

from aiofiles import open as aiopen
from aiofiles.os import makedirs, remove as aioremove
from aioshutil import rmtree
from niquests import AsyncSession

from .... import LOGGER, task_dict, task_dict_lock
from ....core.config_manager import BinConfig, Config
from ...ext_utils.bot_utils import cmd_exec
from ...ext_utils.task_manager import check_running_tasks
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...mirror_leech_utils.status_utils.tldv_status import TldvStatus
from ...telegram_helper.message_utils import send_status_message

_MEETING_RE = r"https?://(?:app\.)?tldv\.io/(?:app/meetings|watch)/([a-zA-Z0-9]+)"


def caesar_decipher(text, offset):
    shift = ((offset % 26) + 26) % 26
    result = []
    for char in text:
        code = ord(char)
        if 65 <= code <= 90:
            result.append(chr(((code - 65 + shift) % 26) + 65))
        elif 97 <= code <= 122:
            result.append(chr(((code - 97 + shift) % 26) + 97))
        else:
            result.append(char)
    return "".join(result)


def parse_tldv_conf(line):
    prefix = "#TLDVCONF:"
    if not line.startswith(prefix):
        raise ValueError(f"Invalid TLDVCONF line: {line}")
    rest = line[len(prefix) :]
    first_comma = rest.find(",")
    second_comma = rest.find(",", first_comma + 1)
    if first_comma == -1 or second_comma == -1:
        raise ValueError(f"Malformed TLDVCONF: {line}")
    expiry = rest[:first_comma]
    offset = int(rest[first_comma + 1 : second_comma])
    base_url = rest[second_comma + 1 :]
    return expiry, offset, base_url


def get_tldv_token(headers=""):
    # -h is a single "key: value key1: value1" string in this bot
    if headers:
        if found := re_search(r"bearer\s+([A-Za-z0-9._\-]+)", headers, IGNORECASE):
            return found.group(1)
        if found := re_search(r"tldvtoken=([^;\s]+)", headers, IGNORECASE):
            return found.group(1)
    return Config.TLDV_TOKEN


def _is_tldv_host(url):
    host = (urlparse(url).hostname or "").lower()
    return host == "tldv.io" or host.endswith(".tldv.io")


class TldvDownloader:
    def __init__(self, listener, path, token=None):
        self.listener = listener
        self._path = path
        self.token = token
        self.meeting_id = None
        self.completed_segments = 0
        self.total_segments = 0
        self.processed_bytes = 0
        self.speed = 0
        self.start_time = None
        self.is_downloading = False
        self.gid = token_hex(5)
        self.name = ""

    @property
    def estimated_total_size(self):
        if self.completed_segments > 0 and self.total_segments > 0:
            return int(
                (self.processed_bytes / self.completed_segments) * self.total_segments
            )
        return 0

    def _headers(self, url):
        # the bearer token only goes to tl;dv itself, never to segment CDN hosts
        if self.token and _is_tldv_host(url):
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    async def _download_segment(self, client, url, index, temp_dir):
        if self.listener.is_cancelled:
            return
        for attempt in range(3):
            try:
                resp = await client.get(url, headers=self._headers(url), timeout=30)
                if resp.status_code != 200:
                    raise Exception(f"HTTP status {resp.status_code}")
                data = resp.content or b""
                async with aiopen(ospath.join(temp_dir, f"seg_{index:05d}.ts"), "wb") as f:
                    await f.write(data)
                self.processed_bytes += len(data)
                if (elapsed := time() - self.start_time) > 0:
                    self.speed = self.processed_bytes / elapsed
                self.completed_segments += 1
                self.listener.size = self.estimated_total_size
                return
            except Exception as e:
                if attempt == 2:
                    raise Exception(
                        f"Failed to download segment {index} after 3 attempts: {e}"
                    )
                await sleep(1)

    async def download(self):
        self.is_downloading = True
        self.start_time = time()

        if not (found := re_search(_MEETING_RE, self.listener.link)):
            await self.listener.on_download_error("Invalid tldv.io URL format")
            return
        self.meeting_id = found.group(1)

        async with AsyncSession() as client:
            meta_url = f"https://gw.tldv.io/v1/meetings/{self.meeting_id}/watch-page?noTranscript=true"
            try:
                resp = await client.get(
                    meta_url, headers=self._headers(meta_url), timeout=20
                )
                if resp.status_code in (401, 403):
                    await self.listener.on_download_error(
                        "Authentication required. Set TLDV_TOKEN or pass -h 'authorization: Bearer TOKEN'."
                    )
                    return
                if resp.status_code != 200:
                    await self.listener.on_download_error(
                        f"Failed to fetch metadata (HTTP {resp.status_code})"
                    )
                    return
                meta_data = resp.json()
            except Exception as e:
                await self.listener.on_download_error(f"Failed to fetch watch-page: {e}")
                return

            meeting = meta_data.get("meeting", {}) if isinstance(meta_data, dict) else {}
            meeting_name = str(meeting.get("name") or "Untitled Meeting")
            created_at = str(meeting.get("createdAt") or "")
            date_str = ""
            if date_match := re_match(r"^(\d{4}-\d{2}-\d{2})", created_at):
                date_str = date_match.group(1) + "_"
            safe_name = re_sub(r'[\\/*?:"<>|]', "", meeting_name).replace(" ", "_")
            self.name = f"{date_str}{safe_name.strip('.') or 'meeting'}.mp4"
            self.listener.name = self.name

            playlist_url = (
                f"https://gaia.tldv.io/v1/meetings/{self.meeting_id}/playlist.m3u8"
            )
            try:
                resp = await client.get(
                    playlist_url, headers=self._headers(playlist_url), timeout=20
                )
                if resp.status_code != 200:
                    await self.listener.on_download_error(
                        f"Failed to fetch playlist (HTTP {resp.status_code})"
                    )
                    return
                playlist_content = resp.text
            except Exception as e:
                await self.listener.on_download_error(f"Failed to fetch playlist: {e}")
                return

            try:
                offset = None
                base_url = None
                segment_urls = []
                for raw_line in playlist_content.split("\n"):
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("#TLDVCONF:"):
                        _, offset, base_url = parse_tldv_conf(line)
                        continue
                    if line.startswith("#"):
                        continue
                    if offset is None or base_url is None:
                        raise ValueError("Segment line found before #TLDVCONF header")
                    segment_urls.append(base_url + caesar_decipher(line, offset))
            except Exception as e:
                await self.listener.on_download_error(f"Failed to parse playlist: {e}")
                return

            self.total_segments = len(segment_urls)
            if self.total_segments == 0:
                await self.listener.on_download_error("No segments found in the playlist")
                return

            temp_dir = ospath.join(self._path, "_tldv_temp")
            await makedirs(temp_dir, exist_ok=True)
            sem = Semaphore(6)

            async def worker(url, idx):
                async with sem:
                    await self._download_segment(client, url, idx, temp_dir)

            try:
                await gather(*(worker(url, i) for i, url in enumerate(segment_urls)))
            except Exception as e:
                if not self.listener.is_cancelled:
                    await self.listener.on_download_error(
                        f"Error downloading segments: {e}"
                    )
                await rmtree(temp_dir, ignore_errors=True)
                return

        if self.listener.is_cancelled:
            await rmtree(temp_dir, ignore_errors=True)
            return

        output_ts = ospath.join(self._path, "output.ts")
        try:
            async with aiopen(output_ts, "wb") as outfile:
                for i in range(self.total_segments):
                    seg_file = ospath.join(temp_dir, f"seg_{i:05d}.ts")
                    if not ospath.exists(seg_file):
                        raise Exception(f"Missing segment {i}")
                    async with aiopen(seg_file, "rb") as infile:
                        await outfile.write(await infile.read())
        except Exception as e:
            await self.listener.on_download_error(f"Failed to merge segments: {e}")
            await rmtree(temp_dir, ignore_errors=True)
            if ospath.exists(output_ts):
                await aioremove(output_ts)
            return

        await rmtree(temp_dir, ignore_errors=True)

        final_mp4 = ospath.join(self._path, self.name)
        cmd = [
            BinConfig.FFMPEG_NAME,
            "-y",
            "-i",
            output_ts,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            final_mp4,
        ]
        _, res_err, code = await cmd_exec(cmd)

        if ospath.exists(output_ts):
            await aioremove(output_ts)

        if code != 0:
            await self.listener.on_download_error(
                f"Remuxing failed with code {code}. Stderr: {res_err}"
            )
            return

        self.listener.size = ospath.getsize(final_mp4)
        await self.listener.on_download_complete()

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling TLDV Download: {self.listener.name}")
        await self.listener.on_download_error("Download Cancelled by User!")


async def add_tldv_download(listener, path, headers=""):
    downloader = TldvDownloader(listener, path, get_tldv_token(headers))
    gid = downloader.gid

    listener.name = "tldv_meeting.mp4"

    add_to_queue, event = await check_running_tasks(listener)
    if add_to_queue:
        LOGGER.info(f"Added to Queue/Download: {listener.name}")
        async with task_dict_lock:
            task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
        await listener.on_download_start()
        if listener.multi <= 1 and not listener.is_rss:
            await send_status_message(listener.message)
        await event.wait()
        if listener.is_cancelled:
            return

    async with task_dict_lock:
        task_dict[listener.mid] = TldvStatus(listener, downloader, gid)

    if add_to_queue:
        LOGGER.info(f"Start Queued Download with TldvDownloader: {listener.name}")
    else:
        LOGGER.info(f"Download with TldvDownloader: {listener.name}")
        await listener.on_download_start()
        if listener.multi <= 1 and not listener.is_rss:
            await send_status_message(listener.message)

    await downloader.download()
