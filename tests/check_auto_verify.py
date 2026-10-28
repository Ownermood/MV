import ast, sys, types, asyncio
REPO = sys.argv[1]
src = open(f"{REPO}/bot/modules/services.py").read()
nodes = [n for n in ast.parse(src).body if (isinstance(n, ast.AsyncFunctionDef) and n.name == "force_join_member_update") or (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "JOINED_STATUSES")]
class CMS: MEMBER = "member"; ADMINISTRATOR = "admin"; OWNER = "owner"; RESTRICTED = "restricted"; LEFT = "left"
state = {"missing": [], "forgot": [], "edits": []}
pending = {}
async def missing_chats(uid, use_cache=True): return state["missing"]
async def edit_message(m, text, markup=None): state["edits"].append((m, text))
ns = {"ChatMemberStatus": CMS, "new_task": lambda f: f, "fsub_chats": lambda: [{"id": "-1004443904846"}, {"id": "-1004293604271"}],
      "forget_user": lambda u: state["forgot"].append(u), "pending_prompts": pending, "missing_chats": missing_chats,
      "edit_message": edit_message, "join_text": lambda m: f"JOIN {m}", "join_markup": lambda u, m: None, "start_home": lambda u: ("HOME", None)}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "x", "exec"), ns)
f = ns["force_join_member_update"]
def upd(chat, uid, status): return types.SimpleNamespace(chat=types.SimpleNamespace(id=int(chat)), new_chat_member=types.SimpleNamespace(user=types.SimpleNamespace(id=uid), status=status))
ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)
async def main():
    pending[9] = "PROMPT"
    state["missing"] = [("Use Bot", "https://t.me/VillanSupport")]
    await f(None, upd("-1004443904846", 9, CMS.MEMBER))
    t("joined 1 of 2 -> prompt updated with what is left", state["edits"][-1] == ("PROMPT", "JOIN [('Use Bot', 'https://t.me/VillanSupport')]") and 9 in pending and 9 in state["forgot"])
    state["missing"] = []
    await f(None, upd("-1004293604271", 9, CMS.MEMBER))
    t("joined both -> prompt becomes the welcome menu", state["edits"][-1] == ("PROMPT", "HOME") and 9 not in pending)
    n = len(state["edits"])
    await f(None, upd("-1009999", 9, CMS.MEMBER)); t("other chats ignored", len(state["edits"]) == n)
    await f(None, upd("-1004443904846", 9, CMS.LEFT)); t("leaving is not a join", len(state["edits"]) == n)
    await f(None, upd("-1004443904846", 77, CMS.MEMBER)); t("user without a prompt: cache cleared, nothing edited", 77 in state["forgot"] and len(state["edits"]) == n)
asyncio.run(main())
print("ALL PASS" if ok else "SOME FAILED")
