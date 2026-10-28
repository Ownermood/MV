# Deploy Mirrorleach Villanbot on a VPS

Tested layout: Ubuntu 22.04/24.04, 2+ GB RAM, 20+ GB disk (downloads need space).

## 1. Install Docker (once)

```bash
sudo apt update && sudo apt install -y git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out and back in after this
docker compose version          # must print a version
```

## 2. Get the code

```bash
git clone https://github.com/Ownermood/MV.git villanbot
cd villanbot
git checkout ccr-2d8f1150-749nfh   # or main, once merged
```

Private repo: use `https://<github-user>:<personal-access-token>@github.com/Ownermood/MV.git`.

## 3. Config

```bash
cp config_sample.py config.py
mkdir -p accounts downloads
nano config.py
```

Required:

| Key | Where to get it |
|---|---|
| `BOT_TOKEN` | @BotFather → /newbot (or /token for @Mirrorleach_Villanbot) |
| `OWNER_ID` | your Telegram user ID (@userinfobot) |
| `TELEGRAM_API`, `TELEGRAM_HASH` | https://my.telegram.org → API development tools |
| `DATABASE_URL` | MongoDB connection string (MongoDB Atlas free tier works). Needed to keep settings across restarts |

Leave `UPSTREAM_REPO` empty. If you set it to this repo, also set `UPSTREAM_BRANCH` to the branch you
deploy (the sample says `wzv3`, which does not exist here).

Optional files go next to `config.py`: `token.pickle`, `rclone.conf`, `cookies.txt`, `accounts/*.json`.

## 4. Base image (optional)

By default the build uses `mysterysd/wzmlx:wzadv` locked to a digest. To use our GHCR copy instead
(made by `.github/workflows/mirror-base-image.yml`), create `.env`:

```bash
echo 'BASE_IMAGE=ghcr.io/ownermood/villanbot-base@sha256:1cb1de42b18361fa7babd7e4d6adef4be0138a7ef5b8126eef581dd3e1efd0bc' > .env
```

If the GHCR package is private, run `docker login ghcr.io` (username + token with `read:packages`) first,
or make the package public in GitHub → Packages → villanbot-base → Package settings.

## 5. Start

```bash
docker compose up -d --build
docker compose logs -f app      # Ctrl+C to stop watching
```

The `tunnel` service gives the web UI (torrent file selector, stream) a public
`trycloudflare.com` URL automatically; no ports need to be opened. For a fixed URL on your own
domain, use the named-tunnel block at the end of `docker-compose.yml`.

Then send `/start` to the bot from the owner account.

## 6. Day to day

| Task | Command |
|---|---|
| Logs | `docker compose logs -f app` |
| Restart | `docker compose restart app` |
| Stop | `docker compose down` |
| Update code | `git pull && docker compose up -d --build` |
| Disk usage | `df -h && du -sh downloads` |
| Checks (no Telegram needed) | `pip install -r tests/requirements.txt && python3 tests/run_checks.py` |

Config changes in `config.py` need `docker compose restart app`; most can also be changed live with
`/bsetting` (stored in the database).

## Troubleshooting

- **Bot does not answer**: `docker compose logs app | tail -50` — usually a wrong `BOT_TOKEN`,
  `TELEGRAM_API`/`TELEGRAM_HASH` or `OWNER_ID`.
- **`manifest unknown` / digest error on build**: the locked base image digest is gone; use the GHCR
  copy (step 4) or update the digest as described in the `Dockerfile`.
- **Disk full**: downloads are in `./downloads`; `/cancelall` and remove leftovers.
