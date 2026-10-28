"""TeraBox share links."""

from niquests import Session
from os import path as ospath
from urllib.parse import parse_qs, urlparse
from re import search
from time import sleep

from ....ext_utils.exceptions import DirectDownloadLinkException
from ._common import user_agent


def terabox(url):
    if "/file/" in url:
        return url

    COOKIE_DOMAINS = (
        "terabox",
        "1024tera",
        "freeterabox",
        "nephobox",
        "4funbox",
        "mirrobox",
        "momerybox",
        "gibibox",
        "goaibox",
        "teraboxapp",
        "terasharelink",
        "teraboxlink",
        "teraboxshare",
        "terafileshare",
    )
    API_PARAMS = {
        "app_id": "250528",
        "web": "1",
        "channel": "dubox",
        "clienttype": "0",
    }

    def __load_cookies():
        cfile = next(
            (f for f in ("terabox.txt", "cookies.txt") if ospath.isfile(f)), None
        )
        if not cfile:
            return None
        cookies = {}
        try:
            with open(cfile) as f:
                for line in f:
                    line = line.rstrip("\r\n")
                    if line.startswith("#HttpOnly_"):
                        line = line[len("#HttpOnly_") :]
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(None, 6)
                    if len(parts) < 7:
                        continue
                    if any(k in parts[0].lower() for k in COOKIE_DOMAINS):
                        cookies[parts[5]] = parts[6]
        except Exception:
            return None
        if not cookies.get("BDUSS") and not cookies.get("ndus"):
            return None
        return cookies

    def __parse_share(share_url):
        parsed = urlparse(share_url)
        qs = parse_qs(parsed.query)
        password = (qs.get("pwd") or [""])[0]
        surl = ""
        if "surl" in qs:
            surl = qs["surl"][0]
        elif "/s/" in parsed.path:
            surl = parsed.path.split("/s/", 1)[1].split("/", 1)[0]
        if surl.startswith("1"):
            surl = surl[1:]
        if not surl:
            raise DirectDownloadLinkException(
                "ERROR: Could not parse Terabox share URL"
            )
        return surl, password

    def __bootstrap(session, surl, password):
        try:
            resp = session.get(
                f"https://www.terabox.com/sharing/link?surl={surl}",
                timeout=30,
                allow_redirects=True,
            )
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        html_text = resp.text
        m = search(r"fn%28%22([0-9A-F]+)%22%29", html_text) or search(
            r'fn\("([0-9A-F]+)"\)', html_text
        )
        if not m:
            raise DirectDownloadLinkException(
                "ERROR: jsToken not found (login expired?)"
            )
        js_token = m.group(1)
        pcf = search(r'pcftoken["\']?\s*[:=]\s*["\']([0-9a-f]+)', html_text)
        pcftoken = pcf[1] if pcf else "0"
        if password:
            try:
                v = session.post(
                    f"https://{resp.url.split('/')[2]}/share/verify",
                    params={**API_PARAMS, "surl": surl},
                    data={"pwd": password},
                    timeout=30,
                ).json()
                if v.get("errno") != 0:
                    raise DirectDownloadLinkException(
                        f"ERROR: Share password verification failed "
                        f"(errno={v.get('errno')})"
                    )
            except DirectDownloadLinkException:
                raise
            except Exception as e:
                raise DirectDownloadLinkException(
                    f"ERROR: {e.__class__.__name__}"
                ) from e
        return js_token, pcftoken

    def __share_list(
        session, surl, js_token, pcftoken, *, dir_path=None, root=False, page=1, num=200
    ):
        params = {
            **API_PARAMS,
            "jsToken": js_token,
            "pcftoken": pcftoken,
            "shorturl": surl,
            "page": str(page),
            "num": str(num),
            "by": "name",
            "order": "asc",
            "scene": "",
        }
        if root:
            params["root"] = "1"
        if dir_path is not None:
            params["dir"] = dir_path
        try:
            data = session.get(
                "https://dm.terabox.com/share/list",
                params=params,
                timeout=30,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if data.get("errno") not in (0, None):
            raise DirectDownloadLinkException(
                f"ERROR: share/list errno={data.get('errno')}"
            )
        return data

    def __shorturlinfo(session, surl, js_token):
        try:
            data = session.get(
                "https://www.terabox.com/api/shorturlinfo",
                params={
                    **API_PARAMS,
                    "jsToken": js_token,
                    "shorturl": f"1{surl}",
                    "root": "1",
                    "page": "1",
                    "num": "20",
                },
                timeout=30,
            ).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if data.get("errno") not in (0, None):
            raise DirectDownloadLinkException(
                f"ERROR: shorturlinfo errno={data.get('errno')}"
            )
        return data

    def __resolve_dlinks(session, js_token, meta, fs_ids):
        out = {}
        for fid in fs_ids:
            try:
                data = session.post(
                    "https://www.terabox.com/share/download",
                    params={
                        **API_PARAMS,
                        "jsToken": js_token,
                        "sign": meta["sign"],
                        "timestamp": str(meta["timestamp"]),
                    },
                    data={
                        "shareid": str(meta["shareid"]),
                        "uk": str(meta["uk"]),
                        "product": "share",
                        "fid_list": f"[{str(fid)}]",
                        "primaryid": str(meta["shareid"]),
                        "type": "nolimit",
                    },
                    timeout=30,
                ).json()
            except Exception as e:
                raise DirectDownloadLinkException(
                    f"ERROR: {e.__class__.__name__}"
                ) from e
            if data.get("errno") not in (0, None):
                raise DirectDownloadLinkException(
                    f"ERROR: share/download errno={data.get('errno')}"
                )
            if data.get("dlink"):
                out[fid] = data["dlink"]
            sleep(0.3)
        return out

    def __crawl_with_cookies(cookies):
        surl, password = __parse_share(url)
        session = Session()
        session.cookies.update(cookies)
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"https://www.terabox.com/sharing/link?surl={surl}",
            }
        )
        js_token, pcftoken = __bootstrap(session, surl, password)
        info = __shorturlinfo(session, surl, js_token)
        meta = {
            "sign": info.get("sign", ""),
            "timestamp": info.get("timestamp", ""),
            "shareid": info.get("shareid") or info.get("share_id"),
            "uk": info.get("uk"),
        }
        details = {"contents": [], "title": "", "total_size": 0}
        pending = []
        base = {"dir": ""}

        def __walk(dir_path=None, root=False):
            page = 1
            while True:
                data = __share_list(
                    session,
                    surl,
                    js_token,
                    pcftoken,
                    dir_path=dir_path,
                    root=root,
                    page=page,
                    num=200,
                )
                if root and page == 1 and not details["title"]:
                    base["dir"] = (data.get("title") or "").rstrip("/")
                    details["title"] = ospath.basename(base["dir"]) or surl
                items = data.get("list") or []
                if not items:
                    break
                for it in items:
                    if int(it.get("isdir") or 0):
                        __walk(dir_path=it["path"])
                    else:
                        parent = ospath.dirname(it.get("path", ""))
                        if base["dir"] and parent.startswith(base["dir"]):
                            parent = parent[len(base["dir"]) :]
                        entry = {
                            "path": parent.strip("/"),
                            "filename": it["server_filename"],
                            "url": it.get("dlink", ""),
                        }
                        details["contents"].append(entry)
                        details["total_size"] += int(it.get("size") or 0)
                        if not entry["url"]:
                            pending.append(
                                (int(it["fs_id"]), len(details["contents"]) - 1)
                            )
                if len(items) < 200:
                    break
                page += 1
                sleep(0.3)

        __walk(root=True)

        if pending:
            resolved = __resolve_dlinks(
                session, js_token, meta, [fid for fid, _ in pending]
            )
            for fid, idx in pending:
                if fid in resolved:
                    details["contents"][idx]["url"] = resolved[fid]
            missing = [
                details["contents"][idx]["filename"]
                for fid, idx in pending
                if fid not in resolved
            ]
            if missing:
                raise DirectDownloadLinkException(
                    f"ERROR: failed to resolve dlink for {len(missing)} "
                    f"file(s); first: {missing[0]}"
                )

        if not details["contents"]:
            raise DirectDownloadLinkException("ERROR: Empty share or invalid cookies")
        if not details["title"]:
            details["title"] = details["contents"][0]["filename"]

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        details["header"] = (
            f"Cookie: {cookie_header}\n"
            f"User-Agent: {user_agent}\n"
            f"Referer: https://www.terabox.com/"
        )
        if len(details["contents"]) == 1:
            return details["contents"][0]["url"], details["header"]
        return details

    cookies = __load_cookies()
    if not cookies:
        raise DirectDownloadLinkException(
            "ERROR: Terabox needs login cookies. Export your terabox.com "
            "cookies (netscape format, must contain ndus) into terabox.txt"
        )
    return __crawl_with_cookies(cookies)
