"""Reset the bot's saved settings in MongoDB, so the next start uses config.py
and the current defaults again.

    docker compose down
    docker compose run --rm app /wzvenv/bin/python reset_settings.py          # settings only
    docker compose run --rm app /wzvenv/bin/python reset_settings.py --all    # everything
    docker compose up -d

Settings only: Bot Settings values, private files, aria2/qBit/SABnzbd options.
Admins, allowed users/groups, RSS and task history stay.
--all: drops the whole bot database (admins, users, groups, RSS, history too).
"""
import sys
from importlib import import_module

from pymongo import MongoClient

SETTINGS = ("config", "deployConfig", "files", "aria2c", "qbittorrent", "nzb")

url = getattr(import_module("config"), "DATABASE_URL", "")
if not url:
    sys.exit("DATABASE_URL is empty in config.py, nothing to reset.")
wipe_all = "--all" in sys.argv
answer = input(
    "Delete ALL bot data (admins, users, groups, settings)? Type YES: "
    if wipe_all
    else "Delete saved Bot Settings (admins/users stay)? Type YES: "
)
if answer.strip() != "YES":
    sys.exit("Cancelled.")
client = MongoClient(url)
if wipe_all:
    client.drop_database("wzmlx")
    print("Done: the whole bot database was deleted.")
else:
    for name in SETTINGS:
        result = client.wzmlx.settings[name].delete_many({})
        print(f"settings.{name}: {result.deleted_count} removed")
    print("Done: settings reset. Start the bot again.")
