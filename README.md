<h1 align="center">Mirror Leech Villan Bot</h1>

<p align="center">
   Telegram mirror &amp; leech bot — <a href="https://t.me/Mirrorleech_Villanbot">@Mirrorleech_Villanbot</a>
</p>

<p align="center">
   Mirror and leech links, Telegram files, torrents, NZB and rclone clouds to Telegram, Google Drive or any rclone remote.
   Built on <a href="https://github.com/SilentDemonSD/WZML-X">WZML-X</a> with security hardening and features merged from
   <a href="https://github.com/anasty17/mirror-leech-telegram-bot">mirror-leech-telegram-bot</a> and
   <a href="https://github.com/Sam-Max/rcmltb">rcmltb</a>.
</p>

## Index

<details open>
   <summary>Table of Contents <kbd>Click Here</kbd></summary>

   - [At a Glance](#at-a-glance)
   - [Why Use It](#why-use-it)
   - [What It Covers](#what-it-covers)
   - [How It Runs](#how-it-runs)
   - [Deployment](#deployment)
   - [Configuration](#configuration)
   - [Project Layout](#project-layout)
   - [Documentation](#documentation)
   - [Support](#support)
   - [Credits](#credits)
   - [License](#license)
</details>

## At a Glance

| Area | Details |
|---|---|
| Runtime | Python Telegram bot + web UI |
| Deployment | Docker & Docker Compose (buildx) |
| Required config | `BOT_TOKEN`, `TELEGRAM_API`, `TELEGRAM_HASH`, `OWNER_ID`, `DATABASE_URL` |
| License | [LICENSE](LICENSE) |

## Why Use It

Mirror Leech Villan Bot is built for users who want a single bot stack that can mirror, leech, manage files, and expose a simple web-based selection flow without stitching together multiple tools. The README focuses on what you need to deploy it quickly, understand the moving parts, and tune the behavior safely.

## What It Covers

| Capability | Outcome |
|---|---|
| Mirroring | Send files to Telegram with a controllable pipeline |
| Leeching | Deliver files in the format you prefer, including document and media workflows |
| File selection UI | Review and select torrent / NZB / upload contents before finalizing |
| Multi-source downloads | Use qBittorrent, Aria2, JDownloader, Mega, NZB, and yt-dlp integrations |
| Storage and upload paths | Push content to Google Drive, Rclone, Mega, and other supported routes |
| Automation | Limit tasks, tune queues, and manage startup updates from one config layer |
| gallery-dl | `/gallerydl` (`/gdl`) and `/gallerydlleech` (`/gdlleech`) for image/media sites; options via `-opt`, `/usetting` or `GALLERY_DL_OPTIONS` |
| Debrid unlock | `-ad` (AllDebrid) and `-tb` (TorBox, `TORBOX_API_KEY`) for filehost links, magnets and `.torrent` files |
| tl;dv recordings | `/mirror` or `/leech` a tldv.io meeting link to get the MP4 (`TLDV_TOKEN` or `-h authorization: Bearer TOKEN`) |
| Rclone file manager | `/rcfm`: storage usage, empty trash, browse, folder size, rename, delete, mkdir, dedupe |
| Admin panel | `/admin` (owner/sudo): welcome text, welcome image, start buttons, guide/source toggles, broadcast with preview, premium emoji test switch |
| Guided /start | Interactive menu: Leech, Mirror, YouTube & Sites, Torrents, Settings & Tasks, All Commands |

## How It Runs

Deploy with Docker and provide the required configuration values. The container takes care of the runtime path, so users only need to build or start the image and set their settings.

<details>
   <summary>What you need <kbd>Click Here</kbd></summary>

   - Docker installed
   - Your Telegram bot token and Telegram API credentials
   - A MongoDB connection string
   - The optional service credentials you want to enable, such as Drive, Rclone, Mega, JDownloader, or SABnzbd
</details>

## Deployment

<details open>
   <summary>VPS / Dedicated Server (Recommended)</summary>

   ```bash
   git clone https://github.com/Ownermood/MV.git
   cd MV
   cp config_sample.py config.py
   # Edit config.py with your values
   docker buildx compose up -d
   ```

   The bot runs behind a Cloudflare quick tunnel by default. Check the tunnel URL:

   ```bash
   docker compose logs tunnel
   ```

   You'll see a `https://*.trycloudflare.com` URL — that's your bot's web UI.

   To stop:

   ```bash
   docker buildx compose down
   ```
</details>

<details>
   <summary>VPS with VPN (Gluetun)</summary>

   1. Uncomment the `gluetun` service in `docker-compose.yml`
   2. Fill in your VPN provider credentials
   3. Set `network_mode: "service:gluetun"` on the `app` service
   4. Start:

   ```bash
   docker buildx compose up -d
   ```

   All traffic (including the cloudflared tunnel) routes through the VPN.
</details>

<details>
   <summary>Multi-Instance (Multiple Bots)</summary>

   Each bot needs its own `config.py` and data volumes. Example for a second bot:

   1. Create `config2.py` with different `BOT_TOKEN`, `OWNER_ID`, etc.
   2. Uncomment `app2` and `tunnel2` in `docker-compose.yml`
   3. Edit volume mounts to use `config2.py` and separate data dirs
   4. Start:

   ```bash
   docker buildx compose up -d
   ```

   Each bot gets its own cloudflared tunnel URL. Admin ports (qBittorrent, SABnzbd) are mapped to different host ports (`127.0.0.1:8091`, etc.).
</details>

<details>
   <summary>Single Container (Manual)</summary>

   ```bash
   git clone https://github.com/Ownermood/MV.git
   cd MV
   docker build -t villanbot .
   docker run -p 8080:8080 villanbot
   ```
</details>

<details>
   <summary>Deployment Notes</summary>

   1. If you use qBittorrent, tune `AsyncIOThreadsCount` to your machine size.
   2. Stop the container before removing it, and remove the container before pruning images.
   3. Useful cleanup commands:

   ```bash
   docker container prune
   docker image prune -a
   ```
</details>

## Configuration

Start with the required values:

- `BOT_TOKEN`
- `TELEGRAM_API`
- `TELEGRAM_HASH`
- `OWNER_ID`
- `DATABASE_URL`

Then tune the optional behavior from `config_sample.py`.

<details>
   <summary>Important user-facing settings</summary>

   | Setting | User impact |
   |---|---|
   | `DEFAULT_LANG` | Bot language |
   | `STATUS_LIMIT` | How much status data is shown |
   | `DEFAULT_UPLOAD` | Default upload target |
   | `LEECH_SPLIT_SIZE` | How large leech outputs are split |
   | `QUEUE_ALL`, `QUEUE_DOWNLOAD`, `QUEUE_UPLOAD` | Queue pressure and concurrency |
   | `SHOW_CLOUD_LINK` | Whether cloud links are shown to users |
   | `WEB_PINCODE` | Protects web access to file selection |
</details>

<details>
   <summary>Integrations available in config</summary>

   The sample config also covers:

   - qBittorrent and Aria2-related controls
   - JDownloader login details
   - Mega credentials
   - SABnzbd server definitions
   - Google Drive settings
   - RSS, search, media metadata, and logging controls
</details>

<details>
   <summary>AllDebrid (<code>-ad</code>)</summary>

   Set `ALLDEBRID_API_KEY` (default: empty, feature off) in `config_sample.py`,
   in the environment, or from **Bot Settings → Config Variables → ALLDEBRID_API_KEY**.

   Add `-ad` to a mirror/leech command to route the input through AllDebrid:

   - `/mirror <filehost link> -ad` unlocks premium hosts (1fichier, rapidgator,
     mega, ...) and hands the direct link to the normal downloader.
   - `/leech <magnet> -ad` (or reply to a `.torrent` with `-ad`) uploads the
     torrent to AllDebrid, waits for it to finish there, then downloads every
     file from AllDebrid's CDN — aria2/qBittorrent are bypassed entirely.

   `ALLDEBRID_NO_SEED_TIMEOUT` (default: `180`) caps how many seconds a magnet may
   stall with no seeders and no download progress before the task is aborted.
   Set it to `0` to disable the check and rely on AllDebrid's own dead-torrent
   reporting instead.

   The flag is documented in the mirror help menu under the **AllDebrid** button.
   Without a key the task fails with `ALLDEBRID_API_KEY is not configured`;
   without `-ad` nothing changes. Magnets stop after 3 min with no seeders and
   2 h overall, and are removed from your AllDebrid history if the task fails.
</details>

## Project Layout

| Path | Purpose |
|---|---|
| `bot/` | Bot core, handlers, listeners, and modules |
| `web/` | FastAPI app, templates, and the file selector UI |
| `gen_scripts/` | Setup helpers for sessions, tokens, and drive configuration |
| `plugins/` | Optional bot plugins |
| `qBittorrent/` | Default qBittorrent configuration |
| `sabnzbd/` | Default SABnzbd configuration |

## Checks

`python3 tests/run_checks.py` runs the security and port checks (sanitizers, unpickler, rclone
filters, symlink cleanup, gallery-dl, TorBox, tl;dv, `/rcfm`) without a Telegram config.
Install `tests/requirements.txt` first; the tl;dv check also needs `ffmpeg`.

## Security Model

| Role | Can do |
|---|---|
| **Owner** (`OWNER_ID`) | Everything: `/shell`, `/exec`, `/aexec`, `/plugins`, add/remove sudo, secret config vars, private files, aria2/qBit/SABnzbd/usenet options |
| **Sudo** | Bot settings (non-secret vars), authorize users/chats, restart, logs, broadcast |
| **Authorized** | Mirror, leech, clone, yt-dlp, search, own user settings |

Hardening applied on top of WZML-X (see `SECURITY_AUDIT.md`):

- Shell/exec/plugins and sudo management are owner-only.
- Sudo users cannot view or edit tokens, session strings, `DATABASE_URL`, `UPSTREAM_REPO`, API keys or passwords.
- No `eval()` on user input; user `token.pickle` files load through a Google-Credentials-only unpickler.
- User-supplied yt-dlp options, FFmpeg commands, rclone flags and rclone configs are filtered so they cannot
  run programs or read/write files outside the task folder (the owner is not restricted).
- The stats version check parses the upstream version as text instead of downloading and running it.
- `-n`/`-m` names, remote file paths from direct/debrid hosts and extracted symlinks cannot reach outside the task folder.
- Crash telemetry to the upstream developers is **off** by default (`ENABLE_TELEMETRY`).

## Credits

- [WZML-X](https://github.com/SilentDemonSD/WZML-X) by SilentDemonSD, RjRiajul, CodeWithWeeb, Maverick and contributors — base of this bot.
- [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot) by anasty17 and contributors — the project WZML-X is built on.
- [rcmltb](https://github.com/Sam-Max/rcmltb) by Sam-Max — rclone features.

## License

AGPL-3.0, inherited from WZML-X (the GPL-3.0 parts from mirror-leech-telegram-bot and rcmltb are combined under
section 13 of both licenses). See [LICENSE](LICENSE). Because this is a network service under the AGPL, users of a
running bot must be able to get its source: the `/start` **Git Repo** button points at this repository, so keep it
reachable.
