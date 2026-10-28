import ast, sys, re
from shlex import split
src = open(sys.argv[1]).read(); tree = ast.parse(src)
keep = [n for n in tree.body if (isinstance(n, ast.Assign) and any(getattr(t,'id','').startswith('_FF_') for t in n.targets)) or (isinstance(n, ast.FunctionDef) and n.name=='unsafe_ffmpeg_token')]
ns={"re":re}; exec(compile(ast.Module(body=keep,type_ignores=[]),"x","exec"),ns); f=ns["unsafe_ffmpeg_token"]
legit = [
 "-i mltb.mkv -c copy -c:s srt mltb.mkv",
 "-i mltb.video -c:v libx264 -crf 23 -vf scale=-2:720 mltb.mp4",
 "-i mltb -vf fps=30000/1001 mltb.mp4",
 "-i mltb.mkv -vf crop=iw/2:ih:0:0 -map 0:v -map 0:a:0 mltb.mkv",
 "-i mltb.audio -c:a libmp3lame -b:a 320k mltb.mp3",
 "-i mltb.mkv -ss 00:01:00 -t 30 -metadata title=Test mltb.mp4 -del",
 "-i mltb.mkv -filter_complex [0:v]setpts=PTS/2[v] -map [v] mltb.mp4",
]
attacks = [
 "-i mltb.mkv -attach /usr/src/app/config.py -c copy mltb.mkv",
 "-i mltb.mkv -c copy -f data /usr/src/app/bot/x.py",
 "-i mltb.mkv -vf drawtext=textfile=/usr/src/app/config.py mltb.mp4",
 "-i mltb.mkv -vf \"subtitles='/etc/passwd'\" mltb.mp4",
 "-i mltb.mkv -i ../../config.py mltb.mkv",
 "-i mltb.mkv -i http://169.254.169.254/latest mltb.mkv",
 "-i mltb.mkv -i file:config.py mltb.mkv",
 "-i mltb.mkv -f tee [f=mp4]/tmp/x.mp4",
 "-i mltb.mkv -i concat:a.mkv|b.mkv mltb.mkv",
 "-i mltb.mkv ~/x.mp4",
 "-i mltb.mkv -i subfile,,start,0,end,10,,:config.py mltb.mkv",
]
ok=True
for c in legit:
    r=f([p for p in split(c) if p]); ok &= r is None; print("PASS" if r is None else f"FAIL(blocked {r!r})","legit:",c)
for c in attacks:
    r=f([p for p in split(c) if p]); ok &= r is not None; print("PASS" if r else "FAIL(allowed)","attack:",c,"->",r)
print("ALL PASS" if ok else "SOME FAILED")
