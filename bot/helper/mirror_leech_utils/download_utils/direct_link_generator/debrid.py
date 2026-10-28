"""Debrid-Link premium link generation."""

from cloudscraper import create_scraper
from os import path as ospath

from .....core.config_manager import Config
from ....ext_utils.exceptions import DirectDownloadLinkException


def debrid_link(url):
    cget = create_scraper().request
    resp = cget(
        "POST",
        f"https://debrid-link.com/api/v2/downloader/add?access_token={Config.DEBRID_LINK_API}",
        data={"url": url},
    ).json()
    if not resp["success"]:
        raise DirectDownloadLinkException(
            f"ERROR: {resp['error']} & ERROR ID: {resp['error_id']}"
        )
    if isinstance(resp["value"], dict):
        return resp["value"]["downloadUrl"]
    elif isinstance(resp["value"], list):
        details = {
            "contents": [],
            "title": ospath.basename(url.rstrip("/")),
            "total_size": 0,
        }
        for dl in resp["value"]:
            if dl.get("expired", False):
                continue
            item = {
                "path": ospath.join(details["title"]),
                "filename": dl["name"],
                "url": dl["downloadUrl"],
            }
            if "size" in dl:
                details["total_size"] += dl["size"]
            details["contents"].append(item)
        return details
