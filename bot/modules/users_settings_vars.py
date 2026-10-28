"""User settings tables: option groups and the help text shown in /usetting."""


from ..core.tg_client import TgClient


clone_options = [
    "USER_SESSION",
    "CLONE_DUMP_CHATS",
    "CLONE_CONTENT_TYPE",
    "CLONE_EXCLUDED_EXTENSIONS",
    "CLONE_FILTERS",
]

leech_options = [
    "LEECH_SPLIT_SIZE",
    "LEECH_DUMP_CHATS",
    "LEECH_PREFIX",
    "LEECH_SUFFIX",
    "LEECH_CAPTION",
]

thumb_options = ["THUMBNAIL", "THUMBNAIL_LAYOUT"]

uphoster_options = [
    "GOFILE_TOKEN",
    "GOFILE_FOLDER_ID",
    "BUZZHEAVIER_TOKEN",
    "BUZZHEAVIER_FOLDER_ID",
    "PIXELDRAIN_KEY",
    "DEVUPLOADS_KEY",
    "DEVUPLOADS_FOLDER",
    "VIKINGFILE_HASH",
    "VIKINGFILE_FOLDER",
]

rclone_options = ["RCLONE_CONFIG", "RCLONE_PATH", "RCLONE_FLAGS"]

gdrive_options = ["TOKEN_PICKLE", "GDRIVE_ID", "INDEX_URL", "DRIVE_CAT"]

ffset_options = [
    "FFMPEG_CMDS",
    "METADATA",
    "AUDIO_METADATA",
    "VIDEO_METADATA",
    "SUBTITLE_METADATA",
]

advanced_options = [
    "EXCLUDED_EXTENSIONS",
    "NAME_SWAP",
    "UPLOAD_PATHS",
]

ytdlp_options = [
    "YT_DLP_OPTIONS",
    "GALLERY_DL_OPTIONS",
    "USER_COOKIE_FILE",
    "YT_DESP",
    "YT_TAGS",
    "YT_CATEGORY_ID",
    "YT_PRIVACY_STATUS",
]

mega_options = ["MEGA_EMAIL", "MEGA_PASSWORD"]

seedr_options = ["SEEDR_EMAIL", "SEEDR_PASSWORD", "SEEDR_DELETE_FOLDER"]

user_settings_text = {
    "THUMBNAIL": (
        "Photo or Doc",
        "Custom Thumbnail is used as the thumbnail for the files you upload to telegram in media or document mode.",
        "<i>Send a photo to save it as custom thumbnail.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_CONFIG": (
        "rclone.conf file",
        "Your own rclone config. Used whenever the task runs in USER mode, or when the path starts with <code>mrcc:</code>.",
        "<i>Send your <code>rclone.conf</code> file to use as your Upload Dest to RClone.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "TOKEN_PICKLE": (
        "token.pickle file",
        "Your own Google Drive token. Used in USER mode, or when the id starts with <code>mtp:</code>.",
        "<i>Send your <code>token.pickle</code> to use as your Upload Dest to GDrive</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_SPLIT_SIZE": (
        "Size, e.g. 2GB",
        "Where a file is cut before upload. Capped at what your account allows, so a bigger number is silently clamped.",
        f"Send Leech split size in bytes or use gb or mb. Example: 40000000 or 2.5gb or 1000mb. PREMIUM_USER: {TgClient.IS_PREMIUM_USER}.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "USER_SESSION": (
        "String Session",
        "Your own telegram session, sealed with a passphrase you choose. The bot "
        "stores only the ciphertext, salt and nonce, never the passphrase and never "
        "the derived key, so a database dump carries nothing usable. After one "
        "unlock the key is held in memory for 12h and is lost on restart. An owner "
        "who patches the running bot can read the plaintext during that window. If "
        "that is not acceptable to you, do not use this.",
        """<i>Send your Pyrogram V2 string session. Generate one with /exportsession.
The message is deleted the moment it arrives.</i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "CLONE_DUMP_CHATS": (
        "Dict",
        "Default destinations for /clone when -ud is not given.",
        """<i>Send a dict of name to chat id. Example: {'Movies': -1001234567890}</i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "CLONE_CONTENT_TYPE": (
        "doc | med | all",
        "Restrict /clone to documents only, media only, or everything.",
        """<i>Send one of: <code>doc</code>, <code>med</code>, <code>all</code></i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "CLONE_EXCLUDED_EXTENSIONS": (
        "Space separated extensions",
        "Extensions skipped by /clone only. Independent of the leech list.",
        """<i>Send extensions separated by space. Example: mkv srt txt</i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "CLONE_FILTERS": (
        "Dict",
        "Regex applied to every /clone task. mn keeps matching names, xn drops "
        "them, mc and xc do the same against the caption.",
        """<i>Send a dict. Example: {'mn': '1080p', 'xc': 'sample'}</i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "LEECH_PREFIX": (
        "Text, HTML allowed",
        "Goes in front of every leeched name. HTML is kept in the caption and stripped from the filename. Write <code>\\s</code> for a space.",
        "Send Leech Filename Prefix. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_SUFFIX": (
        "Text, HTML allowed",
        "Goes after the name, before the extension. Same HTML and <code>\\s</code> rules as the prefix.",
        "Send Leech Filename Suffix. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_CAPTION": (
        "Template, HTML allowed",
        "Replaces the whole caption. Fill in <code>{filename} {size} {duration} {quality} {languages} {subtitles} {md5_hash} {mime_type} {prefilename} {precaption}</code>, then add <code>|find:replace</code> parts to patch the result. Escape a real one with <code>\\|</code> <code>\\{</code> <code>\\}</code>.",
        "Send Leech Caption. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "THUMBNAIL_LAYOUT": (
        "Grid, e.g. 3x3",
        "Grabs frames spread across the video and tiles them into one thumbnail. <code>2x2</code> is 4 frames, <code>3x3</code> is 9.",
        "Send thumbnail layout (widthxheight, 2x2, 3x3, 2x4, 4x4, ...). Example: 3x3.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_PATH": (
        "remote:folder",
        "Default rclone destination. Prefix with <code>mrcc:</code> to force your own config instead of the owner's.",
        "Send Rclone Path. If you want to use your rclone config edit using owner/user config from usetting or add mrcc: before rclone path. Example mrcc:remote:folder. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_FLAGS": (
        "key:value|key",
        "Extra flags passed to every rclone call. Separate them with <code>|</code>, and drop the value for a switch.",
        "key:value|key|key|key:value . Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>\nEx: --buffer-size:8M|--drive-starred-only",
    ),
    "GDRIVE_ID": (
        "Folder or Drive id",
        "Default Google Drive destination. Prefix with <code>mtp:</code> for your own token, <code>tp:</code> for the owner's, <code>sa:</code> for service accounts.",
        "Send Gdrive ID. If you want to use your token.pickle edit using owner/user token from usetting or add mtp: before the id. Example: mtp:F435RGGRDXXXXXX . </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "INDEX_URL": (
        "https:// link",
        "Your index for the drive above. When set, finished tasks also report a direct index link.",
        "Send Index URL for your gdrive option. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "UPLOAD_PATHS": (
        "Dict of aliases",
        "Short names for long destinations. Once set, <code>-up name</code> is swapped for the real path, id or chat behind it.",
        "Send Dict of keys that have path values. Example: {'path 1': 'remote:rclonefolder', 'path 2': 'gdrive1 id', 'path 3': 'tg chat id', 'path 4': 'mrcc:remote:', 'path 5': b:@username} . </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_DUMP_CHATS": (
        "Name and chat id per line",
        "Your own leech dump chats. Every leech gets copied to all of them, and "
        "each is selectable per task by name with -ud. Names are merged over the "
        "owner's list and yours wins a clash. Independent of the clone "
        "destinations. Every chat is checked at set time, so the bot must already "
        "be an admin there.",
        """<i>One per line: <code>Movies -1001234567890</code>
Add a topic with a pipe: <code>Movies -1001234567890|12</code>
A dict works too: <code>{'Movies': -1001234567890}</code></i>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "EXCLUDED_EXTENSIONS": (
        "Space separated",
        "Extensions never uploaded, written without the dot. <code>aria2</code> and <code>!qB</code> are always kept on top of yours. Applies to leech and mirror, not to /clone.",
        "Send excluded extensions separated by space without dot at beginning. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "NAME_SWAP": (
        "pattern:replace|...",
        "Regex rewrites run on every filename before upload, in order. Each rule is <code>pattern:replace:count:flag</code> where count 0 means every match and flag is a name like <code>IGNORECASE</code>. Chain rules with <code>|</code>.",
        """<i>Send your Name Swap. You can add pattern instead of normal text according to the format.</i>
<b>Full Documentation Guide</b> <a href="https://t.me/WZML_X/77">Click Here</a>
┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "YT_DLP_OPTIONS": (
        "Dict of options",
        "Passed straight into yt-dlp for every yt task. API option names, not command line flags.",
        """Format: {key: value, key: value, key: value}.
Example: {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, "playliststart": 10, "fragment_retries": float("inf"), "matchtitle": "S13", "writesubtitles": True, "live_from_start": True, "postprocessor_args": {"ffmpeg": ["-threads", "4"]}, "wait_for_video": (5, 100), "download_ranges": [{"start_time": 0, "end_time": 10}]}
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.

<i>Send dict of YT-DLP Options according to format.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "GALLERY_DL_OPTIONS": (
        "Dict of options",
        "Passed into gallery-dl for every /gallerydl task when no -opt is given.",
        """Format: {key: value, key: value}.
Example: {"image-range": "1-50", "extractor": {"pixiv": {"username": "user", "password": "pass"}}}
Only the bot owner can use postprocessors, config-files, archive, base-directory, output or file paths.
Check gallery-dl options from this <a href='https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst'>FILE</a>.

<i>Send dict of gallery-dl Options according to format.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "FFMPEG_CMDS": (
        "Dict of lists",
        "Named ffmpeg runs applied before upload, picked per task with <code>-ff</code>. Start at the arguments, never at the word ffmpeg, and every command needs an <code>-i</code>.",
        """Dict of list values of ffmpeg commands. You can set multiple ffmpeg commands for all files before upload. Don't write ffmpeg at beginning, start directly with the arguments.
Examples: {"subtitle": ["-i mltb.mkv -c copy -c:s srt mltb.mkv", "-i mltb.video -c copy -c:s srt mltb"], "convert": ["-i mltb.m4a -c:a libmp3lame -q:a 2 mltb.mp3", "-i mltb.audio -c:a libmp3lame -q:a 2 mltb.mp3"], extract: ["-i mltb -map 0:a -c copy mltb.mka -map 0:s -c copy mltb.srt"]}
Notes:
- Add `-del` to the list which you want from the bot to delete the original files after command run complete!
- To execute one of those lists in bot for example, you must use -ff subtitle (list key) or -ff convert (list key)
Here I will explain how to use mltb.* which is reference to files you want to work on.
1. First cmd: the input is mltb.mkv so this cmd will work only on mkv videos and the output is mltb.mkv also so all outputs are mkv. -del will delete the original media after complete run of the cmd.
2. Second cmd: the input is mltb.video so this cmd will work on all videos and the output is only mltb so the extension is the same as input files.
3. Third cmd: the input is mltb.m4a so this cmd will work only on m4a audios and the output is mltb.mp3 so the output extension is mp3.
4. Fourth cmd: the input is mltb.audio so this cmd will work on all audios and the output is mltb.mp3 so the output extension is mp3.

<i>Send dict of FFMPEG_CMDS Options according to format.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "METADATA_CMDS": (
        "Legacy",
        "Replaced by Metadata in FF Media Settings.",
        """<i>Send your Meta data. You can set it according to the format title="Join @Mirrorleach_Villanbot".</i>
<b>Full Documentation Guide</b> <a href="https://t.me/WZML_X/">Click Here</a>
┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "METADATA": (
        "🏷 Global Metadata (key=value|key=value)",
        "Apply metadata to all media files with dynamic variables.",
        """<i>📝 Send metadata as</i> <code>key=value|key2=value2</code>

<b>🔧 Dynamic Variables:</b>
• <code>{filename}</code> - Original filename
• <code>{basename}</code> - Name without extension
• <code>{audiolang}</code> - Audio language (English/Hindi etc.)
• <code>{year}</code> - Year from filename

<b>📋 Example:</b>
<code>title={basename}|artist={audiolang} Version|year={year}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "AUDIO_METADATA": (
        "🎵 Audio Stream Metadata",
        "Metadata applied to each audio track separately.",
        """<i>🎧 Audio stream metadata with per-track language support</i>

<b>📋 Example:</b>
<code>language={audiolang}|title=Audio - {audiolang}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "VIDEO_METADATA": (
        "🎥 Video Stream Metadata",
        "Metadata applied to video streams.",
        """<i>📹 Video stream metadata for visual tracks</i>

<b>📋 Example:</b>
<code>title={basename}|comment=HD Video</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "SUBTITLE_METADATA": (
        "💬 Subtitle Stream Metadata",
        "Metadata applied to each subtitle track separately.",
        """<i>📄 Subtitle stream metadata with per-track language support</i>

<b>📋 Example:</b>
<code>language={sublang}|title=Subtitles - {sublang}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "YT_DESP": (
        "String",
        "Custom description for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube description.</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_TAGS": (
        "Comma-separated strings",
        "Custom tags for YouTube uploads (e.g., tag1,tag2,tag3). Default is used if not set.",
        "<i>Send your custom YouTube tags as a comma-separated list.</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_CATEGORY_ID": (
        "Number",
        "Custom category ID for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube category ID (e.g., 22).</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_PRIVACY_STATUS": (
        "public, private, or unlisted",
        "Custom privacy status for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube privacy status (public, private, or unlisted).</i> \nTime Left : <code>60 sec</code>",
    ),
    "USER_COOKIE_FILE": (
        "File",
        "User's YT-DLP Cookie File to authenticate access to websites and youtube.",
        "<i>Send your cookie file (e.g., cookies.txt or abc.txt).</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "GOFILE_TOKEN": (
        "String",
        "Gofile API Token",
        "<i>Send your Gofile API Token.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "GOFILE_FOLDER_ID": (
        "String",
        "Gofile Folder ID",
        "<i>Send your Gofile Folder ID. If empty, uploads to Root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "BUZZHEAVIER_TOKEN": (
        "String",
        "BuzzHeavier API Token",
        "<i>Send your BuzzHeavier API Token (Account ID).</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "BUZZHEAVIER_FOLDER_ID": (
        "String",
        "BuzzHeavier Folder ID",
        "<i>Send your BuzzHeavier Folder ID.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "PIXELDRAIN_KEY": (
        "String",
        "PixelDrain API Key",
        "<i>Send your PixelDrain API Key.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "DEVUPLOADS_KEY": (
        "String",
        "DevUploads API Key",
        "<i>Send your DevUploads API Key.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "DEVUPLOADS_FOLDER": (
        "String",
        "DevUploads Folder ID",
        "<i>Send your DevUploads Folder ID. Leave empty to upload to root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "VIKINGFILE_HASH": (
        "String",
        "VikingFile Hash",
        "<i>Send your VikingFile User Hash.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "VIKINGFILE_FOLDER": (
        "String",
        "VikingFile folder name/path. Leave empty to upload to root.",
        "<i>Send your VikingFile folder name/path. Leave empty to upload to root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "MEGA_EMAIL": (
        "String",
        "Your Mega.nz account email for per-user Mega downloads & uploads.",
        "<i>Send your Mega.nz email address.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "MEGA_PASSWORD": (
        "String",
        "Your Mega.nz account password for per-user Mega downloads & uploads.",
        "<i>Send your Mega.nz account password.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "SEEDR_EMAIL": (
        "String",
        "Your Seedr.cc account email for per-user Seedr cloud downloads.",
        "<i>Send your Seedr.cc email address.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "SEEDR_PASSWORD": (
        "String",
        "Your Seedr.cc account password for per-user Seedr cloud downloads.",
        "<i>Send your Seedr.cc account password.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "SEEDR_DELETE_FOLDER": (
        "On or Off",
        "Removes the folder from Seedr once the download finishes, so the "
        "account does not fill up. Toggled from the Seedr Tools panel.",
        "<i>Toggle it from the Seedr Tools panel.</i>",
    ),
    "DRIVE_CAT": (
        "Dict",
        'User-defined GDrive categories (name → drive_id). Format: {"name": "drive_id|index_link"}.',
        '<i>Send dict of user drive categories.\nExample: {"Movies": "0Bxxxxxxxx", "TV": "1Ayyyyyyy|https://index.tv"}\nEach value: drive_id or drive_id|index_link</i> \n┖ <b>Time Left :</b> <code>60 sec</code>',
    ),
}
