# Mirror-Leech Telegram Bot Family — Deep Security & Architecture Audit

**Date:** 2026-10-27
**Scope:** Full A-to-Z static analysis of the 7 repos supplied, in priority order.
**Method:** Shallow-cloned each repo, static review of all execution sinks (`eval`/`exec`/`shell=True`/`subprocess`/`pickle`), command-handler authorization filters, option/argument parsing, dependency pinning, and secret handling. No runtime/dynamic exploitation was performed.

> Straight talk, no sugarcoating: **every modern fork in this family shares the same root design flaw — untrusted command arguments are passed to Python `eval()`**, and the whole family inherits an owner/sudo shell + Python `exec` console by design. These bots assume the operator trusts everyone they authorize. That assumption is the entire security model.

---

## 0. Repos analyzed

| # | Repo | Last commit | .py files | ~LOC | Status |
|---|------|-------------|-----------|------|--------|
| 1 | `anasty17/mirror-leech-telegram-bot` | 2026-10-18 | 135 | 28k | Active base |
| 2 | `SilentDemonSD/WZML-X` | 2026-10-04 | 195 | 52k | Active, largest |
| 3 | `Dawn-India/Z-Mirror` | 2025-02-11 | 119 | 37k | Stale ~8 mo |
| 4 | `AeonOrg/Aeon-MLTB` | 2026-04-02 | 128 | 24k | Active |
| 5 | `Sam-Max/rcmltb` | 2026-04-20 | 116 | 21k | Active, rclone-focused |
| 6 | `breakdowns/slam-mirrorbot` | 2023-12-04 | 64 | 8k | **Abandoned 3 yr** |
| 7 | `weebzone/WZML` | — | — | — | **Redirects to WZML-X — identical code, skipped as duplicate** |

Note: `weebzone/WZML` is now a redirect to `SilentDemonSD/WZML-X` (same HEAD commit, byte-identical tree). It is not a separate codebase.

---

## 1. CRITICAL — Authorized-user Remote Code Execution via `eval()` on `-opt`

**Affected:** anasty17, WZML-X (partial), Aeon, Z-Mirror, rcmltb (all modern forks).

The `/ytdl` (and in anasty17/Aeon, `/leech` with gallery-dl) command parses a user-supplied `-opt` argument and passes it **directly to `eval()`**:

```python
# anasty17 bot/modules/ytdlp.py:326
opt = eval(args["-opt"]) if args["-opt"] else {}
# anasty17 bot/modules/gallery_dl.py:93  — same pattern
# Sam-Max/rcmltb bot/modules/ytdlp.py:539
args[key] = eval(opt_str)
# Z-Mirror bot/modules/ytdlp.py:311 + yt_dlp_download.py:482
value = eval(value)
```

**Reachability:** The `/ytdl` handler is gated by `CustomFilters.authorized` — **not** owner/sudo:

```
anasty17 handlers.py:308   & CustomFilters.authorized
WZML-X   handlers.py:410   & CustomFilters.authorized
Aeon     handlers.py:176     CustomFilters.authorized
```

`authorized` includes every user in the `AUTH` list and every member of any AUTH'd group/chat (`filters.py:14` `authorized_user`). That is a **far larger and less-trusted set** than the owner. Any such user can send a Python expression in `-opt` and have it evaluated in the bot process. `eval()` of an arbitrary expression is direct code execution (e.g. an expression that constructs and invokes an object performing I/O, spawns a process, or imports a module). **Confirmed statically; no PoC run.**

Secondary amplifier: even without `eval` abuse, there is **no allowlist/denylist on yt-dlp options**. User options flow unfiltered into `_set_options()` and merge into the live yt-dlp opts dict (`yt_dlp_download.py:345`). yt-dlp's own `exec`/`Exec` postprocessor family executes shell commands by design, so an attacker who controls the options dict gets command execution through yt-dlp itself regardless of the `eval` issue.

### The one fork that got the parser right
**WZML-X uses `ast.literal_eval`, not `eval`**, for `-opt` and `-ff`:
```python
# SilentDemonSD/WZML-X bot/modules/ytdlp.py:360
opt = literal_eval(args["-opt"]) if args["-opt"] else {}
# line 351  value = literal_eval(args["-ff"])
```
`literal_eval` only parses literals and cannot execute code — this closes the direct-eval RCE. **WZML-X is materially safer than its own upstream (anasty17) on this specific vector.** However WZML-X still lacks the yt-dlp option allowlist, so the "options → yt-dlp exec postprocessor" path remains open to authorized users.

### Fix (applies to anasty17, Aeon, Z-Mirror, rcmltb)
1. Replace every `eval(args["-opt"])` / `eval(value)` on user input with `ast.literal_eval` (copy WZML-X's approach — same project idiom, minimal diff).
2. Add a denylist for dangerous yt-dlp keys (`exec`, `exec_before_download`, `Exec*` postprocessors, `postprocessor_args` shell injection, `--external-downloader`, `paths`/`outtmpl` traversal) **after** parsing, before merge.

---

## 2. CRITICAL (design) — `eval` on GD-search callback data

**Affected:** anasty17, Aeon, Z-Mirror.

```python
# anasty17 bot/modules/gd_search.py:71-85
is_recursive = not bool(eval(data[3]))
buttons = await list_buttons(user_id, is_recursive, eval(data[4]))
...
is_recursive = eval(data[3]); user_token = eval(data[4])
```

`data` is the Telegram `callback_data` string split on spaces. Telegram clients can send **arbitrary** `callback_data` to a bot (it is not restricted to bytes the bot emitted). The handler only checks `data[1]` equals the sender's own id — an attacker sets `data[1]` to their own id and injects an expression into `data[3]`/`data[4]`. Result: `eval()` of attacker-controlled text → code execution, reachable by any authorized user who can see a search result. **WZML-X does not use this `eval`-on-callback pattern.**

**Fix:** callback payloads here are only ever `True`/`False`/small lists — parse with `literal_eval` or a strict `data[3] == "True"` comparison.

---

## 3. HIGH — WZML-X grants `/shell`, `/exec`, `/aexec` to SUDO users (not owner)

**Affected:** WZML-X only. This is a trust-boundary regression vs. the rest of the family.

```
WZML-X handlers.py:
  /shell  (MessageHandler)  & CustomFilters.sudo      <-- sudo, not owner
  /exec                     & CustomFilters.sudo
  /aexec                    & CustomFilters.sudo
  /clearlocals              & CustomFilters.sudo
```
(The *edited-message* shell handler at :273 is correctly `owner`, but the primary handler at :266 is `sudo`, so the control is effectively sudo.)

By contrast, **anasty17, Aeon, Z-Mirror, rcmltb, and slam all restrict shell/exec/eval to `owner` only** (`handlers.py` `& CustomFilters.owner`; rcmltb `owner_filter`; slam `CustomFilters.owner_filter`).

Impact: in WZML-X, **any sudo user has a full interactive shell and Python `exec` console on the host** — complete host compromise, not just bot compromise. Sudo is routinely handed to co-admins/helpers who are not the server owner. `/shell` runs via `cmd_exec(cmd, shell=True)` (`bot/modules/shell.py:15`); `/exec`/`/aexec` run `exec(f"async def func():\n...")` (`bot/modules/exec.py:82`).

**Fix:** change these four filters to `CustomFilters.owner`. One-word change per handler; preserves the feature, restores the intended trust boundary.

---

## 4. MEDIUM — `eval()` on config / user-settings input (owner & self-scope)

**Affected:** all modern forks.

```python
# bot_settings.py (anasty17 313/315/383/402, Aeon 257/288/307, Z-Mirror 656/785/810)
value = eval(value)                      # owner-set config values
# users_settings.py (anasty17 449/508, WZML-X 1575/1585, Aeon 467/519)
value = eval(value)                      # per-user {dict} settings (UPLOAD_PATHS, FFMPEG_CMDS, YT_DLP_OPTIONS...)
# bot_utils.py arg_parser  -ff  -> eval(value)  (anasty17:177, Aeon:218)
```

`bot_settings` `eval` is owner-scoped (lower severity — owner already has `/exec`), but it is still unnecessary code execution on config text and will execute whatever the owner pastes (e.g. a config value copied from an untrusted guide). The **`users_settings` eval is per-user** and the `-ff` eval in `arg_parser` is reachable by authorized users (same class as #1). Z-Mirror additionally `eval`s `USENET_SERVERS` and `SEARCH_PLUGINS` from config (`__init__.py:405/486`, `bot_settings.py:1912/1991`).

**Fix:** `literal_eval` everywhere these parse a dict/list/tuple/bool; none of them need full `eval`.

---

## 5. MEDIUM — `eval()` on subprocess output (ffprobe JSON & GDrive error body)

**Affected:** all forks.

```python
# media_utils.py  fields = eval(result[0]).get("format"/"streams")
# gdrive clone/upload/download:  eval(err.content).get("error")...
```

`result[0]` is `ffprobe -print_format json` output for a **user-supplied media file**; `err.content` is a Google API error body. Both are JSON and should be `json.loads`. Using `eval` on the output of a tool processing an attacker-controlled file is a latent injection sink: a maliciously crafted container whose metadata forces ffprobe to emit a non-pure-JSON token (or a bare `true/false/null` outside a string) at minimum crashes the worker (DoS); worst case it is an eval-injection foothold. Low probability (ffprobe normally emits quoted strings), real code smell, trivial to fix.

**Fix:** `json.loads(result[0])` / `json.loads(err.content)`. Pure mechanical, no behavior change on well-formed input.

---

## 6. LOW/INFO — Dependency hygiene

- **All modern forks ship fully unpinned `requirements.txt`** (anasty17 0/35 pinned, Aeon 0/38, Z-Mirror 0/35, rcmltb 0/40, WZML-X 1/40). Combined with `update.py` doing `uv pip install -U -r requirements.txt` on every boot, a single compromised/yanked upstream release is a live supply-chain path into the bot host. **Recommend pinning with hashes** (or at least `==` + a lockfile) for anything running with shell/exec access to a server.
- **slam-mirrorbot is abandoned (Dec 2023) and pins to known-vulnerable versions:** `pyrogram==1.4.16`, `python-telegram-bot==13.15`, `lxml<=4.8.0`, `urllib3<=1.26.15`, `youtube_dl` (unmaintained, superseded by yt-dlp), plus `git+https://github.com/breakdowns/lk21`. These carry multiple published CVEs (lxml/urllib3) and youtube_dl has unpatched extractor issues. **Do not deploy slam; if a feature is needed, port it into anasty17/WZML-X.**
- slam also has a classic `subprocess.run(["7z","a",f"-p{pswd}",...])` pattern — argument-list form so no shell injection, but password appears in the process argv (visible in `ps`/`/proc`). Minor.

## 7. INFO — things that are fine / not findings
- **`pickle.load`** appears only in `generate_drive_token.py` / `add_to_team_drive.py` / `gen_sa_accounts.py` on **local, owner-generated** `token.pickle` / `credentials`. Not attacker-reachable; standard Google-auth flow. No action.
- **Secret logging:** grep of `LOGGER.*(TOKEN|PASSWORD|...)` shows only variable *names* in messages ("Creating client from BOT_TOKEN", "check TMDB_ACCESS_TOKEN"), **no secret values are logged.** Good.
- `cmd_exec(..., shell=True)` in startup/jdownloader/update paths uses **static, non-user strings** (aria2 launch, `uv pip install`, qbittorrent boot). Not injectable. The `/shell` command is `shell=True` **by design** and owner-gated (except WZML-X sudo regression, #3).
- Core command auth model (`authorized`/`sudo`/`owner` in `filters.py`) is otherwise consistent and correctly applied across mirror/leech/clone commands.

---

## 8. Verdict & priority ranking

**Overall family posture:** These are power-user admin tools, not multi-tenant services. The dominant, repeated mistake is **`eval()` instead of `ast.literal_eval()` on anything a non-owner can influence.** Fixing that one pattern removes the only *authorized-user* RCE vectors; everything else is either owner-scoped (and owners already have a shell) or hygiene.

| Rank | Finding | Repos | Who can exploit | Fix effort |
|------|---------|-------|-----------------|------------|
| 1 | `eval(-opt)` RCE (#1) | anasty17, Aeon, Z-Mirror, rcmltb | any **authorized** user | trivial (`literal_eval`) |
| 2 | `eval` on callback data (#2) | anasty17, Aeon, Z-Mirror | any **authorized** user | trivial |
| 3 | `/shell`+`/exec` opened to **sudo** (#3) | **WZML-X** | any **sudo** user | one word per handler |
| 4 | yt-dlp option allowlist missing | all incl. WZML-X | any authorized user | medium |
| 5 | `eval` on config/user settings (#4) | all modern | owner + self | trivial |
| 6 | `eval` on ffprobe/API output (#5) | all | crafted-file (DoS+) | trivial |
| 7 | unpinned deps / slam CVEs (#6) | all / slam | supply-chain | medium |

**Per-repo takeaway:**
- **anasty17** (base): clean architecture, but carries findings #1, #2, #4, #5, #6. The `eval(-opt)` authorized-user RCE is the one to fix first.
- **WZML-X** (recommended fork): **best `-opt` handling in the family** (`literal_eval`), avoids #2 — but has the **worst shell/exec authorization (#3, sudo not owner)** and still needs the yt-dlp option allowlist. Fix #3 and it is the strongest of the set.
- **Z-Mirror:** stale (~8 mo), carries all `eval` findings; lower priority to deploy.
- **Aeon:** mirrors anasty17's findings; actively maintained.
- **rcmltb:** `eval(-opt)` present; rclone focus otherwise sound.
- **slam-mirrorbot:** **abandoned + vulnerable deps — do not deploy.**
- **weebzone/WZML:** duplicate of WZML-X.

---

*Static analysis only — no exploits executed, no runtime verification. Findings are code-path confirmed via source review; severity reflects reachability by trust tier (owner > sudo > authorized).*

---

## 9. Status in this repo (Mirror Leech Villan Bot, based on WZML-X wzv3)

Everything above describes the upstream projects. This repo is WZML-X plus the fixes below; each is a
separate commit on this branch. Findings found during the merge (not in the sections above) are marked *new*.

| Issue | Status here |
|---|---|
| #1 `eval(-opt)` / yt-dlp options | WZML-X already used `literal_eval`; non-owner yt-dlp options now drop Exec postprocessors, external downloaders, ffmpeg location/args, paths/outtmpl, cookie files, file URLs, netrc_cmd |
| #2 `eval` on GD-search callbacks | Not present in WZML-X |
| #3 `/shell` `/exec` `/aexec` for sudo | Owner-only again; also `/addsudo`, `/rmsudo`, `/plugins` |
| #4 `eval` in settings | Remaining `eval` in user settings replaced with `literal_eval`; no `eval` left in `bot/` |
| #5 `eval` on ffprobe/API output | Not present in WZML-X |
| *new* sudo reads/edits secrets in `/bsetting` | Tokens, session string, DB URL, API keys, passwords, `UPSTREAM_REPO`, private files, git push: owner-only (enforced on the callback) |
| *new* qBit `autorun_program` / SABnzbd scripts via `/bsetting` | aria2/qBit/SABnzbd/usenet option view/edit is owner-only |
| *new* user `token.pickle` loaded with `pickle.load` | Restricted unpickler: Google Credentials classes only |
| *new* user FFmpeg cmds read/write host files | Absolute paths, traversal and protocols refused for non-owners; ffmpeg runs inside the task folder |
| *new* user rclone flags / rclone.conf | `--password-command`, `--config`, `--rc`, file flags dropped; `local`/`alias` remotes, `*command*`/`ssh` options and local paths refused |
| *new* `-n` / `-m` path traversal | Names kept to one path component |
| *new* remote paths from direct/debrid hosts | Joined paths cannot leave the task folder |
| *new* archive symlinks | Links pointing outside the extraction folder are removed |
| *new* `/stats` ran upstream `version.py` | Version parsed as text, never executed |
| *new* AllDebrid key in chat errors | Masked |
| *new* telemetry uploads recent logs | `ENABLE_TELEMETRY` defaults to False |
| *new* AllDebrid/TorBox wait could not be cancelled | Resolution is listed in `/status` and stoppable with `/cancel` |
| #6 unpinned dependencies | **Still open** — see below |

Ported features carry their own fixes: gallery-dl (`literal_eval`, option scrubbing, serialized jobs),
TorBox (key masked in errors), tl;dv (TLS verification on, token only sent to tldv.io).

**Still open, with reasons:**
- Dependencies are unpinned and `update.py` upgrades them on boot. Pinning needs the versions in the
  `mysterysd/wzmlx:wzadv` base image; no Docker daemon was available here and Docker Hub rate-limited the
  registry API, so they could not be read. Pinning blindly can break the build. To get them:
  `docker run --rm --entrypoint /wzvenv/bin/python mysterysd/wzmlx:wzadv -m pip freeze` and pin
  `requirements.txt` to that output.
- The Docker base image is a third-party prebuilt image (`mysterysd/wzmlx:wzadv`). It is now locked to
  digest `sha256:1cb1de42…0bc`, so a changed tag cannot slip in; the image contents are still the
  upstream developer's. Full control needs our own base image.
- Nothing here was run against live Telegram; checks use stubs (`python3 tests/run_checks.py`).
