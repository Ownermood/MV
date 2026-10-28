import ast, sys, re
from configparser import RawConfigParser
src = open(sys.argv[1]).read(); tree = ast.parse(src)
keep = [n for n in tree.body if (isinstance(n, ast.Assign) and any(getattr(t,'id','')=='_UNSAFE_RC_FLAG' for t in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name in ("unsafe_rclone_flag","unsafe_rclone_config"))]
ns = {"re_compile": re.compile, "IGNORECASE": re.IGNORECASE, "RawConfigParser": RawConfigParser}
exec(compile(ast.Module(body=keep,type_ignores=[]),"x","exec"), ns)
fl, cf = ns["unsafe_rclone_flag"], ns["unsafe_rclone_config"]
ok = True
def t(name, cond):
    global ok; ok &= cond; print("PASS" if cond else "FAIL", name)
for f,v in [("--transfers","8"),("--checkers","16"),("--buffer-size","64M"),("--drive-chunk-size","128M"),("--drive-server-side-across-configs",""),("--retries","3"),("--tpslimit","10"),("--fast-list",""),("--drive-keep-revision-forever",""),("--bwlimit","10M"),("--exclude","*.txt"),("--order-by","size,desc"),("--max-age","2d")]:
    t(f"legit flag {f} {v}", not fl(f, v))
for f,v in [("--password-command","id"),("--metadata-mapper","x"),("--config","/x.conf"),("--log-file","bot/x.py"),("--files-from","/etc/passwd"),("--rc",""),("--rc-addr",":5572"),("--sftp-ssh","sh"),("--ca-cert","/x"),("--cpuprofile","x"),("--dump","headers"),("--cache-dir","x"),("--temp-dir","x"),("--copy-links",""),("-L",""),("--drive-service-account-file","x"),("--backup-dir","/usr/src/app"),("--backup-dir","../x"),("--webdav-bearer-token-command","id"),("--include-from","x")]:
    t(f"blocked flag {f} {v}", fl(f, v))
good = """[gd]
type = drive
scope = drive
token = {"access_token":"x","token_type":"Bearer","refresh_token":"1//r","expiry":"2026-01-01T00:00:00Z"}
team_drive = 0AB
[enc]
type = crypt
remote = gd:secret/folder
password = abc
[un]
type = union
upstreams = gd:a gd:b:ro
[od]
type = onedrive
token = {"a":"b"}
drive_id = x
drive_type = personal
"""
t("legit multi-remote conf", cf(good) is None)
bad = {
 "local": "[x]\ntype = local\n",
 "alias": "[x]\ntype = alias\nremote = /usr/src/app\n",
 "sftp ssh": "[x]\ntype = sftp\nssh = sh -c id\n",
 "webdav cmd": "[x]\ntype = webdav\nurl = https://a\nbearer_token_command = id\n",
 "crypt local": "[x]\ntype = crypt\nremote = /usr/src/app\npassword = a\n",
 "crypt relative local": "[x]\ntype = crypt\nremote = bot\npassword = a\n",
 "crypt on-the-fly": "[x]\ntype = crypt\nremote = :local:/usr/src/app\npassword = a\n",
 "crypt connstr": "[x]\ntype = crypt\nremote = gd,ssh='id':x\npassword = a\n",
 "union local upstream": "[x]\ntype = union\nupstreams = gd:a /usr/src/app\n",
 "chunker traversal": "[x]\ntype = chunker\nremote = gd:../../x\n",
 "sa file abs": "[x]\ntype = drive\nservice_account_file = /usr/src/app/accounts/0.json\n",
 "garbage": "not an ini [[[",
}
for n, c in bad.items():
    r = cf(c); t(f"blocked conf {n} -> {r}", r is not None)
print("ALL PASS" if ok else "SOME FAILED")
