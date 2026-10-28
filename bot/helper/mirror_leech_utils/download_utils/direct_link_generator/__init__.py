"""Direct link generator: maps a link's domain to its site handler.

Site handlers live in the sibling modules, grouped by kind.
"""

from urllib.parse import urlparse

from .....core.config_manager import Config
from ....ext_utils.exceptions import DirectDownloadLinkException
from ..url_shortener_bypass import bypass_shortener, is_url_shortener
from ....ext_utils.links_utils import is_share_link
from ._common import debrid_link_supported_sites
from .debrid import debrid_link
from .file_hosts import akmfiles, berkasdrive, buzzheavier, devuploads, easyupload, fichier, fuckingfast_dl, github, hxfile, krakenfiles, lulacloud, mediafile, mediafire, onedrive, osdn, pcloud, pixeldrain, qiwi, racaty, shrdsk, solidfiles, sourceforge, tmpsend, uploadee, uploadhaven, yandex_disk
from .folder_hosts import gofile, linkBox, send_cm, swisstransfer, transfer_it, wetransfer
from .gdrive_index import filepress, gdflix, hubcloud, hubdrive, sharer_scraper
from .terabox import terabox
from .video_hosts import doods, filelions_and_streamwish, instagram, mp4upload, streamhub, streamtape, streamvid


def direct_link_generator(link):
    """direct links generator"""
    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    elif is_url_shortener(domain):
        resolved = bypass_shortener(link)
        try:
            return direct_link_generator(resolved)
        except DirectDownloadLinkException as e:
            if str(e).startswith("ERROR: No Direct link function found"):
                return resolved
            raise
    elif Config.DEBRID_LINK_API and any(
        x in domain for x in debrid_link_supported_sites
    ):
        return debrid_link(link)
    elif "yadi.sk" in link or "disk.yandex." in link:
        return yandex_disk(link)
    elif any(x in domain for x in ("buzzheavier.com", "bzzhr.co", "bzzhr.to")):
        return buzzheavier(link)
    elif "gdflix" in domain:
        return gdflix(link)
    elif "hubdrive" in domain:
        return hubdrive(link)
    elif "hubcloud" in domain:
        return hubcloud(link)
    elif "devuploads" in domain:
        return devuploads(link)
    elif "lulacloud.com" in domain:
        return lulacloud(link)
    elif "uploadhaven" in domain:
        return uploadhaven(link)
    elif "fuckingfast.co" in domain:
        return fuckingfast_dl(link)
    elif "mediafile.cc" in domain:
        return mediafile(link)
    elif "mediafire.com" in domain:
        return mediafire(link)
    elif "osdn.net" in domain:
        return osdn(link)
    elif "sourceforge.net" in domain:
        return sourceforge(link)
    elif "github.com" in domain:
        return github(link)
    elif "transfer.it" in domain:
        return transfer_it(link)
    elif "hxfile.co" in domain:
        return hxfile(link)
    elif "1drv.ms" in domain:
        return onedrive(link)
    elif any(x in domain for x in ["pixeldrain.com", "pixeldra.in"]):
        return pixeldrain(link)
    elif "racaty" in domain:
        return racaty(link)
    elif "1fichier.com" in domain:
        return fichier(link)
    elif "solidfiles.com" in domain:
        return solidfiles(link)
    elif "krakenfiles.com" in domain:
        return krakenfiles(link)
    elif "upload.ee" in domain:
        return uploadee(link)
    elif "gofile.io" in domain:
        return gofile(link)
    elif "send.cm" in domain:
        return send_cm(link)
    elif "tmpsend.com" in domain:
        return tmpsend(link)
    elif "easyupload.io" in domain:
        return easyupload(link)
    elif "streamvid.net" in domain:
        return streamvid(link)
    elif "shrdsk.me" in domain:
        return shrdsk(link)
    elif "u.pcloud.link" in domain:
        return pcloud(link)
    elif "qiwi.gg" in domain:
        return qiwi(link)
    elif "mp4upload.com" in domain:
        return mp4upload(link)
    elif "berkasdrive.com" in domain:
        return berkasdrive(link)
    elif "swisstransfer.com" in domain:
        return swisstransfer(link)
    elif "instagram.com" in domain:
        return instagram(link)
    elif any(x in domain for x in ["akmfiles.com", "akmfls.xyz"]):
        return akmfiles(link)
    elif any(
        x in domain
        for x in [
            "dood.watch",
            "doodstream.com",
            "dood.to",
            "dood.so",
            "dood.cx",
            "dood.la",
            "dood.ws",
            "dood.sh",
            "doodstream.co",
            "dood.pm",
            "dood.wf",
            "dood.re",
            "dood.video",
            "dooood.com",
            "dood.yt",
            "doods.yt",
            "dood.stream",
            "doods.pro",
            "ds2play.com",
            "d0o0d.com",
            "ds2video.com",
            "do0od.com",
            "d000d.com",
        ]
    ):
        return doods(link)
    elif any(
        x in domain
        for x in [
            "streamtape.com",
            "streamtape.co",
            "streamtape.cc",
            "streamtape.to",
            "streamtape.net",
            "streamta.pe",
            "streamtape.xyz",
        ]
    ):
        return streamtape(link)
    elif any(x in domain for x in ["wetransfer.com", "we.tl"]):
        return wetransfer(link)
    elif any(
        x in domain
        for x in [
            "terabox.com",
            "nephobox.com",
            "4funbox.com",
            "mirrobox.com",
            "momerybox.com",
            "teraboxapp.com",
            "1024tera.com",
            "terabox.app",
            "gibibox.com",
            "goaibox.com",
            "terasharelink.com",
            "teraboxlink.com",
            "freeterabox.com",
            "1024terabox.com",
            "teraboxshare.com",
            "terafileshare.com",
            "terabox.club",
        ]
    ):
        return terabox(link)
    elif any(
        x in domain
        for x in [
            "filelions.co",
            "filelions.site",
            "filelions.live",
            "filelions.to",
            "mycloudz.cc",
            "cabecabean.lol",
            "filelions.online",
            "embedwish.com",
            "kitabmarkaz.xyz",
            "wishfast.top",
            "streamwish.to",
            "kissmovies.net",
        ]
    ):
        return filelions_and_streamwish(link)
    elif any(x in domain for x in ["streamhub.ink", "streamhub.to"]):
        return streamhub(link)
    elif any(
        x in domain
        for x in [
            "linkbox.to",
            "lbx.to",
            "teltobx.net",
            "telbx.net",
            "linkbox.cloud",
        ]
    ):
        return linkBox(link)
    elif is_share_link(link):
        return filepress(link) if "filepress" in domain else sharer_scraper(link)
    elif any(
        x in domain
        for x in [
            "anonfiles.com",
            "zippyshare.com",
            "letsupload.io",
            "hotfile.io",
            "bayfiles.com",
            "megaupload.nz",
            "letsupload.cc",
            "filechan.org",
            "myfile.is",
            "vshare.is",
            "rapidshare.nu",
            "lolabits.se",
            "openload.cc",
            "share-online.is",
            "upvid.cc",
            "uptobox.com",
            "uptobox.fr",
        ]
    ):
        raise DirectDownloadLinkException(f"ERROR: R.I.P {domain}")
    else:
        raise DirectDownloadLinkException(f"No Direct link function found for {link}")
