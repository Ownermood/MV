"""Shared constants and helpers for the direct link generators."""

from lxml.etree import HTML
from re import findall
from niquests import post

from ....ext_utils.exceptions import DirectDownloadLinkException


user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
)

debrid_link_supported_sites = [
    "1fichier.com",
    "anonfiles.com",
    "bayfiles.com",
    "clicknupload.link",
    "clicknupload.org",
    "clicknupload.co",
    "clicknupload.cc",
    "clicknupload.download",
    "clicknupload.club",
    "dailyuploads.net",
    "ddl.to",
    "ddownload.com",
    "ddownload.link",
    "drop.download",
    "dropbox.com",
    "dropboxusercontent.com",
    "easyupload.io",
    "emload.com",
    "file.al",
    "fileaxa.com",
    "filecat.net",
    "filedot.to",
    "filedot.xyz",
    "filextras.com",
    "filer.net",
    "filespace.com",
    "filestore.me",
    "gigapeta.com",
    "gofile.io",
    "hexupload.net",
    "hitfile.net",
    "hulkshare.com",
    "isra.cloud",
    "katfile.com",
    "kshared.com",
    "mediafire.com",
    "mega.nz",
    "mega.co.nz",
    "mexashare.com",
    "mixdrop.co",
    "mixdrop.to",
    "mixdrop.sx",
    "mixdrop.club",
    "modsbase.com",
    "nelion.me",
    "pixeldrain.com",
    "prefiles.com",
    "racaty.net",
    "rapidgator.net",
    "rapidgator.asia",
    "rg.to",
    "scribd.com",
    "send.cm",
    "sharemods.com",
    "silkfiles.com",
    "soundcloud.com",
    "streamtape.com",
    "terabox.com",
    "teraboxapp.com",
    "tezfiles.com",
    "turb.cc",
    "turb.to",
    "turbobit.net",
    "turbobit.cc",
    "turbobit.pw",
    "turbobit.online",
    "turbobit.ru",
    "turbobit.live",
    "trubobit.com",
    "turboblt.co",
    "uloz.to",
    "ulozto.net",
    "ulozto.sk",
    "ulozto.cz",
    "upload.ee",
    "uploadhaven.com",
    "up-4ever.com",
    "up-4ever.net",
    "uptobox.com",
    "uptobox.fr",
    "uptobox.eu",
    "uptobox.link",
    "uptostream.com",
    "uptostream.fr",
    "uptostream.eu",
    "uptostream.link",
    "upvid.pro",
    "upvid.live",
    "upvid.host",
    "upvid.biz",
    "upvid.cloud",
    "uqload.com",
    "uqload.co",
    "uqload.io",
    "userload.co",
    "usersdrive.com",
    "vidoza.net",
    "voe.sx",
    "voe-unblock.com",
    "voeunblock1.com",
    "voeunblock2.com",
    "voeunblock3.com",
    "voeunbl0ck.com",
    "voeunblck.com",
    "voeunblk.com",
    "voe-un-block.com",
    "voeun-block.net",
    "workupload.com",
    "world-bytez.com",
    "worldbytez.com",
    "world-files.com",
    "wupfile.com",
    "zippyshare.com",
]

def get_captcha_token(session, params):
    recaptcha_api = "https://www.google.com/recaptcha/api2"
    res = session.get(f"{recaptcha_api}/anchor", params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token := anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return None
    params["c"] = anchor_token[0]
    params["reason"] = "q"
    res = session.post(f"{recaptcha_api}/reload", params=params)
    if token := findall(r'"rresp","(.*?)"', res.text):
        return token[0]

def cf_bypass(url):
    "DO NOT ABUSE THIS"
    try:
        data = {"cmd": "request.get", "url": url, "maxTimeout": 60000}
        _json = post(
            "https://cf.jmdkh.eu.org/v1",
            headers={"Content-Type": "application/json"},
            json=data,
        ).json()
        if _json["status"] == "ok":
            return _json["solution"]["response"]
    except Exception as e:
        e
    raise DirectDownloadLinkException("ERROR: Con't bypass cloudflare")
