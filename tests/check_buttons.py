"""Button rows: short labels keep the asked number per row; a label too long
to show whole next to others gets its own row; order never changes."""
import importlib.util, sys, types

REPO = sys.argv[1]
spec = importlib.util.spec_from_file_location("bb", f"{REPO}/bot/helper/telegram_helper/button_build.py")
bb = importlib.util.module_from_spec(spec); spec.loader.exec_module(bb)

ok = True
def t(n, c):
    global ok; ok &= bool(c); print("PASS" if c else "FAIL", n)


def rows(labels, cols, **kw):
    b = bb.ButtonMaker()
    for x in labels:
        b.data_button(x, "d")
    return [[x.text for x in r] for r in b.build_menu(cols, **kw).inline_keyboard]


t("short labels: 2 a row", rows(["Leech", "Mirror", "Clone", "YT"], 2) == [["Leech", "Mirror"], ["Clone", "YT"]])
t("long label alone", rows(["Disable Auto Thumbnail", "Layout", "Back"], 2) == [["Disable Auto Thumbnail"], ["Layout", "Back"]])
t("3 a row", rows(["aac", "alac", "flac", "m4a", "opus"], 3) == [["aac", "alac", "flac"], ["m4a", "opus"]])
t("Audio Formats does not squeeze into 3", rows(["MP3", "Audio Formats", "Best"], 3) == [["MP3", "Audio Formats"], ["Best"]])
t("page numbers stay 5 a row", rows([str(i) for i in range(1, 11)], 5) == [["1", "2", "3", "4", "5"], ["6", "7", "8", "9", "10"]])
order = rows(["a" * 20, "b", "c", "d" * 20, "e"], 2)
t(f"order kept {order}", sum(order, []) == ["a" * 20, "b", "c", "d" * 20, "e"])
b = bb.ButtonMaker(); b.data_button("Back", "x", "footer"); b.data_button("Close", "y", "footer")
t("footer Back/Close together", [[x.text for x in r] for r in b.build_menu(2).inline_keyboard] == [["Back", "Close"]])
print("ALL PASS" if ok else "SOME FAILED")
