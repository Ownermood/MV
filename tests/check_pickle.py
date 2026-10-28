import ast, sys, io, pickle, datetime
from pickle import Unpickler, UnpicklingError
src = open(sys.argv[1]).read(); tree = ast.parse(src)
keep = [n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ("_TokenUnpickler","load_token_pickle")]
ns = {"Unpickler":Unpickler,"UnpicklingError":UnpicklingError}
exec(compile(ast.Module(body=keep,type_ignores=[]),"x","exec"), ns); load = ns["load_token_pickle"]
from google.oauth2.credentials import Credentials
c = Credentials(token="t", refresh_token="r", token_uri="https://oauth2.googleapis.com/token", client_id="i", client_secret="s", scopes=["https://www.googleapis.com/auth/drive"])
c.expiry = datetime.datetime(2026,1,1)
ok = True
for proto in range(0, 6):
    try:
        got = load(io.BytesIO(pickle.dumps(c, protocol=proto)))
        r = isinstance(got, Credentials) and got.refresh_token == "r" and got.expiry == c.expiry
    except Exception as e:
        r = False; print("  err", e)
    ok &= r; print("PASS" if r else "FAIL", "real token proto", proto)
class Evil:
    def __reduce__(self):
        import os; return (os.getcwd, ())
for proto in range(0, 6):
    try:
        load(io.BytesIO(pickle.dumps(Evil(), protocol=proto))); r = False
    except UnpicklingError as e:
        r = "Blocked posix.getcwd" in str(e) or "Blocked os.getcwd" in str(e)
    ok &= r; print("PASS" if r else "FAIL", "evil blocked proto", proto)
# also the file the user would actually upload from gen script path
print("ALL PASS" if ok else "SOME FAILED")
