import ast, sys, logging, os
from os import path as ospath, unlink, walk
REPO, W = sys.argv[1], sys.argv[2]
os.makedirs(f"{W}/secret"); os.makedirs(f"{W}/task/sub")
open(f"{W}/secret/config.py", "w").write("TOKEN\n"); open(f"{W}/task/real.txt", "w").write("ok")
for target, link in ((f"{W}/secret/config.py", "abs_out.py"), ("../secret/config.py", "rel_out.py"), (f"{W}/secret", "sub/dir_out"),
                     ("real.txt", "inside.txt"), ("sub", "inside_dir"), ("rel_out.py", "chain.py")):
    os.symlink(target, f"{W}/task/{link}")
src = open(f"{REPO}/bot/helper/ext_utils/files_utils.py").read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "remove_escaping_links")
ns = {"ospath": ospath, "unlink": unlink, "walk": walk, "LOGGER": logging.getLogger("t")}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "x", "exec"), ns)
ns["remove_escaping_links"](f"{W}/task")
left = sorted(os.path.relpath(os.path.join(d, n), f"{W}/task") for d, ds, fs in os.walk(f"{W}/task") for n in ds + fs)
ok = left == ["inside.txt", "inside_dir", "real.txt", "sub"] and open(f"{W}/secret/config.py").read() == "TOKEN\n"
print("left:", left)
print("ALL PASS" if ok else "SOME FAILED")
