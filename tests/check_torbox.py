import sys, types, importlib.util, asyncio, threading, json, http.server, logging
from urllib.parse import urlparse, parse_qs
REPO = sys.argv[1]
TOKEN = "tb_SECRET_123"
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
class DDLE(Exception): pass
mod("bot", LOGGER=logging.getLogger("t")); mod("bot.core")
mod("bot.core.config_manager", Config=type("C", (), {"TORBOX_API_KEY": TOKEN}))
mod("bot.helper"); mod("bot.helper.ext_utils"); mod("bot.helper.ext_utils.exceptions", DirectDownloadLinkException=DDLE)
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.download_utils")
name = "bot.helper.mirror_leech_utils.download_utils.torbox_resolver"
spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/helper/mirror_leech_utils/download_utils/torbox_resolver.py")
tb = importlib.util.module_from_spec(spec); sys.modules[name] = tb; spec.loader.exec_module(tb)
tb._POLL_INTERVAL = 0.05
state = {"polls": 0, "auth": [], "deleted": [], "fail_requestdl": False}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        state["auth"].append(self.headers.get("Authorization"))
        n = int(self.headers.get("Content-Length") or 0); body = self.rfile.read(n)
        p = urlparse(self.path).path
        if p.endswith("/torrents/createtorrent"):
            ok = b"magnet:?xt" in body
            return self._send(200, {"success": ok, "data": {"torrent_id": 77} if ok else None, "detail": "bad magnet"})
        if p.endswith("/torrents/controltorrent"):
            state["deleted"].append(body.decode()); return self._send(200, {"success": True, "data": None})
        self._send(404, {"success": False})
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path.endswith("/torrents/mylist"):
            state["polls"] += 1
            ready = state["polls"] >= 2
            item = {"id": 77, "name": "Big Buck Bunny", "download_state": "cached" if ready else "downloading", "seeds": 3, "peers": 1,
                    "files": [{"id": 1, "name": "Big Buck Bunny/bbb.mp4", "short_name": "bbb.mp4", "size": 1000},
                              {"id": 2, "name": "Big Buck Bunny/sub.srt", "short_name": "sub.srt", "size": 10}] if ready else []}
            return self._send(200, {"success": True, "data": item})
        if u.path.endswith("/torrents/requestdl"):
            if state["fail_requestdl"]: return self._send(500, {"success": False})
            assert q["token"] == [TOKEN]
            return self._send(200, {"success": True, "data": f"https://cdn.example/{q['file_id'][0]}"})
        self._send(404, {"success": False})
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
tb._API_BASE = f"http://127.0.0.1:{srv.server_port}/v1/api"
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
async def main():
    r = await tb.torbox_resolve_magnet("magnet:?xt=urn:btih:abc")
    t(f"resolved title={r['title']} id={r['torbox_torrent_id']}", r["title"] == "Big Buck Bunny" and r["torbox_torrent_id"] == 77)
    urls = sorted(c["url"] for c in r["contents"])
    t(f"direct links {urls}", urls == ["https://cdn.example/1", "https://cdn.example/2"])
    t("total size", r["total_size"] == 1010)
    t("auth via Bearer header", all(a == f"Bearer {TOKEN}" for a in state["auth"]))
    try:
        await tb.torbox_resolve_magnet("not-a-magnet"); t("bad magnet raises", False)
    except DDLE as e:
        t(f"API error surfaced: {e}", "bad magnet" in str(e))
    state["fail_requestdl"] = True; state["polls"] = 5; state["deleted"].clear()
    try:
        await tb.torbox_resolve_magnet("magnet:?xt=urn:btih:abc"); t("requestdl 500 raises", False)
    except DDLE as e:
        msg = str(e)
        t(f"requestdl failure message has no token: {msg[:110]}", TOKEN not in msg and "ERROR:" in msg)
    t(f"torrent deleted from TorBox after failure ({state['deleted']})", any("77" in d for d in state["deleted"]))
    cancelled = {"v": False}
    state["fail_requestdl"] = False; state["polls"] = -100
    async def cancel_soon(): await asyncio.sleep(0.2); cancelled["v"] = True
    asyncio.get_running_loop().create_task(cancel_soon())
    try:
        await tb.torbox_resolve_magnet("magnet:?xt=urn:btih:abc", is_cancelled=lambda: cancelled["v"]); t("cancel raises", False)
    except DDLE as e:
        t(f"cancel stops polling: {e}", "cancelled" in str(e))
asyncio.run(main()); srv.shutdown()
print("ALL PASS" if ok else "SOME FAILED")
