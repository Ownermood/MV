import ast, sys, logging
src = open(sys.argv[1]).read()
tree = ast.parse(src)
keep = [n for n in tree.body if (isinstance(n, ast.Assign) and any(getattr(t,'id','').startswith('UNSAFE_') for t in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name == 'sanitize_ytdlp_options')]
ns = {"LOGGER": logging.getLogger("t")}
exec(compile(ast.Module(body=keep, type_ignores=[]), "x", "exec"), ns)
f = ns["sanitize_ytdlp_options"]
ok = True
def check(name, got, exp):
    global ok
    r = got == exp; ok &= r
    print(("PASS" if r else "FAIL"), name, got if not r else "")
check("benign kept", f({"format":"bv*+ba","writesubtitles":True,"playliststart":10}), {"format":"bv*+ba","writesubtitles":True,"playliststart":10})
check("exec pp dropped, ffmpeg pp kept", f({"postprocessors":[{"key":"Exec","exec_cmd":"x"},{"key":"FFmpegMetadata"}]}), {"postprocessors":[{"key":"FFmpegMetadata"}]})
check("single dict pp normalized", f({"postprocessors":{"key":"ExecAfterDownload"}}), {"postprocessors":[]})
check("exec_cmd smuggled under other key", f({"postprocessors":[{"key":"FFmpegMetadata","exec_cmd":"x"}]}), {"postprocessors":[]})
check("dangerous keys dropped", f({"paths":{"home":"/"},"outtmpl":"/x","external_downloader":"aria2c","enable_file_urls":True,"cookiefile":"/etc/x","postprocessor_args":{"ffmpeg":["-attach","/x"]},"netrc_cmd":"id","format":"b"}), {"format":"b"})
check("non-dict input", f("[1,2]"), {})
check("empty", f({}), {})
print("ALL PASS" if ok else "SOME FAILED")
