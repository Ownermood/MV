import ast, sys, asyncio, types
REPO = sys.argv[1]
class FloodWait(Exception):
    def __init__(s, v): s.value = v
class UserIsBlocked(Exception): pass
class InputUserDeactivated(Exception): pass
src = open(f"{REPO}/bot/modules/broadcast.py").read()
nodes = [n for n in ast.parse(src).body if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ("_send_one", "run_broadcast")) or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "BC_STATUS")]
behaviour = {1: ["ok"], 2: ["blocked"], 3: ["flood", "ok"], 4: ["flood", "flood"], 5: ["deact"], 6: ["boom"], 7: ["ok"]}
removed, edits, sleeps = [], [], []
class Rply:
    async def copy(self, uid, disable_notification=False):
        act = behaviour[uid].pop(0)
        if act == "ok": return types.SimpleNamespace(id=uid * 10)
        if act == "flood": raise FloodWait(0)
        if act == "blocked": raise UserIsBlocked()
        if act == "deact": raise InputUserDeactivated()
        raise RuntimeError("boom")
class DB:
    async def get_pm_uids(self): return list(behaviour)
    async def rm_pm_user(self, uid): removed.append(uid)
async def send_message(m, text): return "status"
async def edit_message(m, text): edits.append(text)
async def sleep(v): sleeps.append(v)
ns = {"FloodWait": FloodWait, "UserIsBlocked": UserIsBlocked, "InputUserDeactivated": InputUserDeactivated, "database": DB(),
      "send_message": send_message, "edit_message": edit_message, "sleep": sleep, "time": lambda: 0, "token_hex": lambda n: "bc1",
      "bc_cache": {}, "get_readable_time": lambda s: "0s", "LOGGER": types.SimpleNamespace(error=lambda *a: None)}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "x", "exec"), ns)
bc = asyncio.run(ns["run_broadcast"](Rply(), "msg"))
final = edits[-1]
import re
stats = dict(re.findall(r"<b>([A-Za-z ]+):</b> <code>(\d+)</code>", final))
ok = (bc == "bc1" and stats == {"Total Users": "7", "Success": "3", "Blocked Users": "1", "Deleted Accounts": "1", "Unsuccess Attempt": "2"}
      and sorted(removed) == [2, 5] and len(sleeps) == 2 and ns["bc_cache"]["bc1"] == [(1, 10), (3, 30), (7, 70)])
print(stats, "removed", removed, "sleeps", len(sleeps))
print("ALL PASS" if ok else "SOME FAILED")
