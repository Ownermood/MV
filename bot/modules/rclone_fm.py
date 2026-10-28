# Rclone file manager: browse remotes, storage usage, empty trash, size,
# rename, delete, mkdir and dedupe. Merges rcmltb's /storage, /cleanup and
# /myfiles into one menu.
from html import escape
from json import loads

from aiofiles.os import path as aiopath

from ..core.config_manager import BinConfig
from ..helper.ext_utils.bot_utils import cmd_exec, new_task, safe_path_name
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import edit_message, send_message
from ..helper.telegram_helper.prompt import STOP, PromptUnreachable, ask_in_pm

PAGE_SIZE = 10
fm_state = {}


async def _configs_for(message):
    # A user's own rclone.conf is always theirs to manage; the owner's
    # rclone.conf is only offered to the owner and sudo users.
    user_id = message.from_user.id
    configs = []
    if await aiopath.exists(own := f"rclone/{user_id}.conf"):
        configs.append(("My Config", own))
    if await aiopath.exists("rclone.conf") and await CustomFilters.sudo("", message):
        configs.append(("Owner Config", "rclone.conf"))
    return configs


async def _rclone(*args):
    stdout, stderr, code = await cmd_exec([BinConfig.RCLONE_NAME, *args])
    if code != 0:
        raise RuntimeError(stderr or stdout or f"rclone exited with {code}")
    return stdout


def _full(state, path=None):
    path = state["path"] if path is None else path
    return f"{state['remote']}:{path}"


def _join(base, name):
    return f"{base}/{name}" if base else name


def _btn(state):
    return lambda action, arg="": f"rcfm {state['uid']} {action} {arg}".strip()


async def _show_configs(message, state, configs):
    cb = _btn(state)
    buttons = ButtonMaker()
    for i, (label, _) in enumerate(configs):
        buttons.data_button(label, cb("cfg", i))
    buttons.data_button("Close", cb("close"), "footer")
    await edit_message(message, "<b>Rclone File Manager</b>\nChoose a config:", buttons.build_menu(2))


async def _show_remotes(message, state):
    cb = _btn(state)
    try:
        out = await _rclone("listremotes", "--config", state["conf"])
    except RuntimeError as e:
        await edit_message(message, f"<b>Error:</b> <code>{escape(str(e))}</code>")
        return
    state["remotes"] = [r.rstrip(":") for r in out.split() if r.strip()]
    if not state["remotes"]:
        await edit_message(message, "No remotes found in this rclone config.")
        return
    buttons = ButtonMaker()
    for i, remote in enumerate(state["remotes"]):
        buttons.data_button(remote, cb("rem", i))
    if len(state["configs"]) > 1:
        buttons.data_button("Configs", cb("home"), "footer")
    buttons.data_button("Close", cb("close"), "footer")
    await edit_message(message, "<b>Rclone File Manager</b>\nChoose a remote:", buttons.build_menu(2))


async def _show_remote_menu(message, state):
    cb = _btn(state)
    buttons = ButtonMaker()
    buttons.data_button("Browse", cb("ls"))
    buttons.data_button("Storage", cb("about"))
    buttons.data_button("Empty Trash", cb("trash"))
    buttons.data_button("Back", cb("remotes"), "footer")
    buttons.data_button("Close", cb("close"), "footer")
    await edit_message(
        message, f"<b>Remote:</b> <code>{escape(state['remote'])}</code>", buttons.build_menu(2)
    )


async def _show_dir(message, state, refresh=True):
    cb = _btn(state)
    if refresh:
        try:
            out = await _rclone(
                "lsjson", "--no-mimetype", "--config", state["conf"], _full(state)
            )
            items = loads(out or "[]")
        except Exception as e:
            await edit_message(message, f"<b>Error:</b> <code>{escape(str(e))}</code>")
            return
        items.sort(key=lambda x: (not x.get("IsDir"), x.get("Name", "").lower()))
        state["items"] = items
        state["page"] = 0
    items = state["items"]
    pages = max(1, -(-len(items) // PAGE_SIZE))
    page = min(state["page"], pages - 1)
    buttons = ButtonMaker()
    for idx in range(page * PAGE_SIZE, min(len(items), (page + 1) * PAGE_SIZE)):
        item = items[idx]
        label = f"📁 {item['Name']}" if item.get("IsDir") else f"📄 {item['Name']}"
        buttons.data_button(label[:60], cb("it", idx))
    if page > 0:
        buttons.data_button("⫷", cb("pg", page - 1), "l_body")
    if page < pages - 1:
        buttons.data_button("⫸", cb("pg", page + 1), "l_body")
    buttons.data_button("New Folder", cb("mk"), "header")
    buttons.data_button("Folder Size", cb("size"), "header")
    buttons.data_button("Dedupe", cb("dedupe"), "header")
    if state["path"]:
        buttons.data_button("Delete Folder", cb("rmdir"), "header")
        buttons.data_button("Up", cb("up"), "footer")
    else:
        buttons.data_button("Back", cb("remote"), "footer")
    buttons.data_button("Close", cb("close"), "footer")
    text = (
        f"<b>Path:</b> <code>{escape(_full(state))}</code>\n"
        f"<b>Items:</b> {len(items)} | <b>Page:</b> {page + 1}/{pages}"
    )
    await edit_message(message, text, buttons.build_menu(1, h_cols=2))


async def _show_file(message, state, idx):
    cb = _btn(state)
    item = state["items"][idx]
    buttons = ButtonMaker()
    buttons.data_button("Rename", cb("rn", idx))
    buttons.data_button("Delete", cb("rm", idx))
    buttons.data_button("Back", cb("ls"), "footer")
    buttons.data_button("Close", cb("close"), "footer")
    text = (
        f"<b>File:</b> <code>{escape(_join(state['path'], item['Name']))}</code>\n"
        f"<b>Size:</b> {get_readable_file_size(item.get('Size', 0))}"
    )
    await edit_message(message, text, buttons.build_menu(2))


async def _confirm(message, state, text, yes_action, arg=""):
    cb = _btn(state)
    buttons = ButtonMaker()
    buttons.data_button("Yes, do it", cb(yes_action, arg))
    buttons.data_button("Cancel", cb("ls" if state.get("in_dir") else "remote"))
    await edit_message(message, text, buttons.build_menu(2))


async def _ask_name(user_id, prompt):
    try:
        reply = await ask_in_pm(user_id, prompt)
    except PromptUnreachable:
        return None, "Start the bot in private chat first."
    if reply in (None, STOP):
        return None, None
    name = safe_path_name(reply)
    if not name or name != reply.strip():
        return None, "Name must not be empty or contain '/', '\\' or be '.'/'..'."
    return name, None


async def _run(message, state, busy_text, *args):
    state["busy"] = True
    await edit_message(message, busy_text)
    try:
        return await _rclone(*args)
    finally:
        state["busy"] = False


@new_task
async def rclone_fm(_, message):
    user_id = message.from_user.id
    configs = await _configs_for(message)
    if not configs:
        await send_message(
            message, "Upload your rclone.conf in /usetting (Rclone Config) first."
        )
        return
    menu = await send_message(message, "<i>Loading...</i>")
    state = fm_state[user_id] = {
        "uid": user_id,
        "configs": configs,
        "conf": configs[0][1],
        "remote": "",
        "path": "",
        "items": [],
        "page": 0,
        "busy": False,
    }
    if len(configs) > 1:
        await _show_configs(menu, state, configs)
    else:
        await _show_remotes(menu, state)


@new_task
async def rclone_fm_cb(_, query):
    data = query.data.split()
    message = query.message
    user_id = query.from_user.id
    if int(data[1]) != user_id:
        await query.answer("This menu is not for you!", show_alert=True)
        return
    state = fm_state.get(user_id)
    if state is None:
        await query.answer("Menu expired, send the command again.", show_alert=True)
        return
    if state["busy"]:
        await query.answer("Please wait, previous action is running.", show_alert=True)
        return
    action = data[2]
    arg = int(data[3]) if len(data) > 3 and data[3].isdigit() else None
    await query.answer()
    try:
        await _dispatch(message, state, action, arg)
    except IndexError:
        await edit_message(message, "Menu is out of date, send the command again.")
    except RuntimeError as e:
        state["busy"] = False
        await edit_message(message, f"<b>Error:</b> <code>{escape(str(e))[:3500]}</code>")


async def _dispatch(message, state, action, arg):
    conf = state["conf"]
    if action == "close":
        fm_state.pop(state["uid"], None)
        await edit_message(message, "Rclone File Manager closed.")
    elif action == "home":
        await _show_configs(message, state, state["configs"])
    elif action == "cfg":
        state["conf"] = state["configs"][arg][1]
        await _show_remotes(message, state)
    elif action == "remotes":
        await _show_remotes(message, state)
    elif action == "rem":
        state["remote"], state["path"], state["in_dir"] = state["remotes"][arg], "", False
        await _show_remote_menu(message, state)
    elif action == "remote":
        state["in_dir"] = False
        await _show_remote_menu(message, state)
    elif action == "about":
        out = await _run(message, state, "<i>Fetching storage info...</i>", "about", "--json", "--config", conf, f"{state['remote']}:")
        info = loads(out or "{}")
        lines = [f"<b>Storage of</b> <code>{escape(state['remote'])}</code>"]
        for key in ("total", "used", "free", "trashed", "other"):
            if key in info:
                lines.append(f"<b>{key.title()}:</b> {get_readable_file_size(info[key])}")
        if len(lines) == 1:
            lines.append("No quota info (unlimited or unsupported).")
        buttons = ButtonMaker()
        buttons.data_button("Back", _btn(state)("remote"))
        await edit_message(message, "\n".join(lines), buttons.build_menu(1))
    elif action == "trash":
        await _confirm(message, state, f"Permanently empty the trash of <code>{escape(state['remote'])}</code>?", "trashy")
    elif action == "trashy":
        await _run(message, state, "<i>Emptying trash...</i>", "cleanup", "--config", conf, f"{state['remote']}:")
        buttons = ButtonMaker()
        buttons.data_button("Back", _btn(state)("remote"))
        await edit_message(message, "Trash emptied.", buttons.build_menu(1))
    elif action == "ls":
        state["in_dir"] = True
        await _show_dir(message, state)
    elif action == "pg":
        state["page"] = arg
        await _show_dir(message, state, refresh=False)
    elif action == "up":
        state["path"] = state["path"].rsplit("/", 1)[0] if "/" in state["path"] else ""
        await _show_dir(message, state)
    elif action == "it":
        item = state["items"][arg]
        if item.get("IsDir"):
            state["path"] = _join(state["path"], item["Name"])
            await _show_dir(message, state)
        else:
            await _show_file(message, state, arg)
    elif action == "rm":
        name = state["items"][arg]["Name"]
        await _confirm(message, state, f"Delete <code>{escape(name)}</code>?", "rmy", arg)
    elif action == "rmy":
        name = state["items"][arg]["Name"]
        await _run(message, state, "<i>Deleting...</i>", "deletefile", "--config", conf, _full(state, _join(state["path"], name)))
        await _show_dir(message, state)
    elif action == "rmdir":
        await _confirm(message, state, f"Delete folder <code>{escape(_full(state))}</code> and everything in it?", "rmdiry")
    elif action == "rmdiry":
        await _run(message, state, "<i>Deleting folder...</i>", "purge", "--config", conf, _full(state))
        state["path"] = state["path"].rsplit("/", 1)[0] if "/" in state["path"] else ""
        await _show_dir(message, state)
    elif action == "size":
        out = await _run(message, state, "<i>Calculating size...</i>", "size", "--json", "--config", conf, _full(state))
        info = loads(out or "{}")
        buttons = ButtonMaker()
        buttons.data_button("Back", _btn(state)("ls"))
        await edit_message(
            message,
            f"<b>Path:</b> <code>{escape(_full(state))}</code>\n"
            f"<b>Files:</b> {info.get('count', 0)}\n"
            f"<b>Size:</b> {get_readable_file_size(info.get('bytes', 0))}",
            buttons.build_menu(1),
        )
    elif action == "dedupe":
        await _confirm(message, state, f"Remove duplicate files in <code>{escape(_full(state))}</code> (keeps the newest copy)?", "dedupey")
    elif action == "dedupey":
        await _run(message, state, "<i>Removing duplicates...</i>", "dedupe", "--dedupe-mode", "newest", "--config", conf, _full(state))
        await _show_dir(message, state)
    elif action in ("mk", "rn"):
        old = state["items"][arg]["Name"] if action == "rn" else None
        prompt = (
            f"Send the new name for <code>{escape(old)}</code>"
            if old
            else f"Send the new folder name for <code>{escape(_full(state))}</code>"
        )
        await edit_message(message, "<i>Waiting for the name in private chat...</i>")
        name, error = await _ask_name(state["uid"], prompt)
        if name:
            if old:
                await _rclone("moveto", "--config", conf, _full(state, _join(state["path"], old)), _full(state, _join(state["path"], name)))
            else:
                await _rclone("mkdir", "--config", conf, _full(state, _join(state["path"], name)))
        elif error:
            await send_message(message, error)
        await _show_dir(message, state)
