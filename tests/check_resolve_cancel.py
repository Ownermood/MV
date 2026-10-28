import ast, sys, types, asyncio, logging, importlib.util
REPO = sys.argv[1]
def mod(name, **attrs):
    m = types.ModuleType(name); m.__path__ = []; m.__dict__.update(attrs); sys.modules[name] = m; return m
class MS: STATUS_DOWNLOAD = "Download"; STATUS_QUEUEDL = "QueueDl"; STATUS_QUEUEUP = "QueueUp"
mod("bot", LOGGER=logging.getLogger("t")); mod("bot.helper"); mod("bot.helper.ext_utils")
mod("bot.helper.ext_utils.status_utils", get_readable_file_size=str, MirrorStatus=MS, EngineStatus=lambda: types.SimpleNamespace(STATUS_QUEUE="QSystem"))
mod("bot.helper.mirror_leech_utils"); mod("bot.helper.mirror_leech_utils.status_utils")
name = "bot.helper.mirror_leech_utils.status_utils.queue_status"
spec = importlib.util.spec_from_file_location(name, f"{REPO}/bot/helper/mirror_leech_utils/status_utils/queue_status.py")
qs = importlib.util.module_from_spec(spec); sys.modules[name] = qs; spec.loader.exec_module(qs)
# pull Mirror._track_resolve/_untrack_resolve out of mirror_leech.py
src = open(f"{REPO}/bot/modules/mirror_leech.py").read()
cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "Mirror")
meths = [n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name in ("_track_resolve", "_untrack_resolve")]
task_dict, lock = {}, asyncio.Lock()
ns = {"task_dict": task_dict, "task_dict_lock": lock, "ResolveStatus": qs.ResolveStatus, "token_hex": lambda n: "g1"}
tree = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name="M", bases=[], keywords=[], body=meths, decorator_list=[], type_params=[])], type_ignores=[]))
exec(compile(tree, "x", "exec"), ns)
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
class L(ns["M"]):
    def __init__(self): self.mid, self.name, self.size, self.is_cancelled, self.msgs = 7, "", 0, False, []
    async def on_download_error(self, e, *a, **k):
        async with lock: task_dict.pop(self.mid, None)
        self.msgs.append(e)
async def resolver(listener, outcome):
    for _ in range(50):
        if listener.is_cancelled: raise Exception("ERROR: cancelled")
        await asyncio.sleep(0.01)
    if outcome == "error": raise Exception("ERROR: dead torrent")
    return {"contents": []}
async def flow(listener, outcome):
    # same shape as the TorBox block in mirror_leech.new_event
    await listener._track_resolve("TorBox")
    try:
        resolved = await resolver(listener, outcome)
    except Exception as e:
        if listener.is_cancelled:
            return "cancelled"
        listener.msgs.append(str(e)); return "error"
    finally:
        await listener._untrack_resolve()
    return "ok"
async def main():
    a = L(); task = asyncio.create_task(flow(a, "ok")); await asyncio.sleep(0.05)
    st = task_dict.get(7)
    t(f"listed in /status while resolving (engine={getattr(st,'engine',None)}, status={st.status() if st else None})", st and st.engine == "TorBox" and st.status() == "Download" and st.gid() == "g1")
    await st.task().cancel_task()
    r = await task
    t(f"/cancel stops resolve ({r}), single message {a.msgs}", r == "cancelled" and a.msgs == ["Stopped by User!"] and 7 not in task_dict)
    b = L(); r = await flow(b, "error")
    t(f"error path: entry removed, error sent ({b.msgs})", r == "error" and 7 not in task_dict and b.msgs == ["ERROR: dead torrent"])
    c = L(); r = await flow(c, "ok")
    t("success path: entry removed for the download engine", r == "ok" and 7 not in task_dict)
    task_dict[7] = "DirectStatus"; d = L(); await d._untrack_resolve()
    t("untrack never removes another engine's status", task_dict.get(7) == "DirectStatus")
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
