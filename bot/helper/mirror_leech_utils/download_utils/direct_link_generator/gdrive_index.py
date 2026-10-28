"""GDrive index / mirror sites: HubCloud, HubDrive, GDFlix, FilePress, sharer."""

from curl_cffi import Session as CurlSession
from lxml.etree import HTML
from cloudscraper import create_scraper
from re import findall
from niquests import get, post
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from ....ext_utils.exceptions import DirectDownloadLinkException
from ....ext_utils.status_utils import speed_string_to_bytes
from .file_hosts import buzzheavier


def _hubcloud_links(session, url):
    try:
        tree = HTML(session.get(url).text)
        if gen := tree.xpath("//a[@id='download']/@href"):
            tree = HTML(session.get(gen[0]).text)
        return [
            h
            for h in tree.xpath("//a[contains(@class, 'btn-lg')]/@href")
            if h.startswith("http") and "vdplay" not in h
        ]
    except Exception:
        return []

def _first_alive(session, links):
    fallback = ""
    for durl in links:
        try:
            if "bzzhr.co" in durl:
                return buzzheavier(durl)
            res = session.head(durl, timeout=20)
            if inner := parse_qs(urlparse(res.url).query).get("link"):
                durl = inner[0]
                res = session.head(durl, timeout=20)
            if res.status_code < 400 and "text/html" not in res.headers.get(
                "content-type", ""
            ):
                return durl
            fallback = fallback or durl
        except Exception:
            continue
    return fallback

def hubcloud(url):
    with CurlSession(impersonate="chrome") as session:
        if durl := _first_alive(session, _hubcloud_links(session, url)):
            return durl
    raise DirectDownloadLinkException("ERROR: File Not Found or Expired")

def hubdrive(url):
    parsed = urlparse(url)
    file_id = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    host = f"{parsed.scheme}://{parsed.netloc}"
    links = []
    with CurlSession(impersonate="chrome") as session:
        tree = HTML(session.get(url).text)
        if "/packs/" in url:
            details = {
                "contents": [],
                "title": (tree.xpath("//title/text()") or [""])[0]
                .split("|")[-1]
                .strip(),
                "total_size": 0,
            }
            for row in tree.xpath("//div[contains(@class, 'pack-clean-file')]"):
                name = row.xpath(".//div[contains(@class, 'pack-clean-title')]/text()")
                size = row.xpath(".//div[contains(@class, 'pack-clean-size')]/text()")
                item = row.xpath(".//a[contains(@class, 'pack-clean-link')]/@href")
                if not name or not item:
                    continue
                details["contents"].append(
                    {
                        "path": "",
                        "filename": name[0].strip(),
                        "url": hubdrive(f"{host}{item[0]}"),
                    }
                )
                details["total_size"] += speed_string_to_bytes(
                    size[0].strip() if size else "0b"
                )
            if not details["contents"]:
                raise DirectDownloadLinkException("ERROR: No files found in pack")
            return details
        try:
            res = session.post(
                f"{host}/ajax.php?ajax=direct-download",
                data={"id": file_id},
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": url},
            )
            if gd := res.json().get("data", {}).get("gd"):
                links.append(gd)
        except Exception:
            pass
        if mirror := tree.xpath("//a[contains(@href, 'hubcloud')]/@href"):
            links += _hubcloud_links(session, mirror[0])
        if durl := _first_alive(session, links):
            return durl
    raise DirectDownloadLinkException("ERROR: File Not Found or Expired")

def gdflix(url):
    with CurlSession(impersonate="chrome") as session:
        res = session.get(url)
        tree = HTML(res.text)
        if "/pack/" in url:
            host = f"https://{urlparse(res.url).netloc}"
            details = {
                "contents": [],
                "title": (tree.xpath("//title/text()") or [""])[0]
                .split("|")[-1]
                .strip(),
                "total_size": 0,
            }
            for link in tree.xpath("//a[starts-with(@href, '/file/')]"):
                name, _, size = " ".join(link.itertext()).strip().rpartition("[")
                details["contents"].append(
                    {
                        "path": "",
                        "filename": name.strip(),
                        "url": gdflix(f"{host}{link.attrib['href']}"),
                    }
                )
                details["total_size"] += speed_string_to_bytes(size.strip("] "))
            if not details["contents"]:
                raise DirectDownloadLinkException("ERROR: No files found in pack")
            return details
        if not (instant := tree.xpath("//a[contains(@href, 'instant')]/@href")):
            raise DirectDownloadLinkException("ERROR: Instant DL link not found")
        res = session.get(instant[0], allow_redirects=False)
        if not (loc := res.headers.get("location", "").strip()):
            raise DirectDownloadLinkException("ERROR: File Not Found or Expired")
        if durl := parse_qs(urlparse(loc).query).get("url"):
            return durl[0]
        return loc

def filepress(url):
    try:
        url = get(f"https://filebee.xyz/file/{url.split('/')[-1]}").url
        raw = urlparse(url)
        json_data = {
            "id": raw.path.split("/")[-1],
            "method": "publicDownlaod",
        }
        api = f"{raw.scheme}://{raw.hostname}/api/file/downlaod/"
        res2 = post(
            api,
            headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
            json=json_data,
        ).json()
        json_data2 = {
            "id": res2["data"],
            "method": "publicDownlaod",
        }
        api2 = f"{raw.scheme}://{raw.hostname}/api/file/downlaod2/"
        res = post(
            api2,
            headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
            json=json_data2,
        ).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e

    if "data" not in res:
        raise DirectDownloadLinkException(f"ERROR: {res['statusText']}")
    return f"https://drive.google.com/uc?id={res['data']}&export=download"

def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        header = {
            "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"
        }
        res = cget("GET", url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    key = findall(r'"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not HTML(res.text).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException(
            "ERROR: This link don't have direct download button"
        )
    boundary = uuid4()
    headers = {
        "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
        "x-token": raw.hostname,
        "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10",
    }

    data = (
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n'
        f"------WebKitFormBoundary{boundary}--\r\n"
    )
    try:
        res = cget("POST", url, cookies=res.cookies, headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if "url" not in res:
        raise DirectDownloadLinkException(
            "ERROR: Drive Link not found, Try in your browser"
        )
    if "drive.google.com" in res["url"] or "drive.usercontent.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget("GET", res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if (drive_link := HTML(res.text).xpath("//a[contains(@class,'btn')]/@href")) and (
        "drive.google.com" in drive_link[0]
        or "drive.usercontent.google.com" in drive_link[0]
    ):
        return drive_link[0]
    else:
        raise DirectDownloadLinkException(
            "ERROR: Drive Link not found, Try in your browser"
        )
