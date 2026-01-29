import os
import asyncio
import time
import math
import subprocess

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")

DOWNLOAD_DIR = "downloads"
ENCODE_DIR = "encoded"
CHUNK_MB = 5
AUTO_DELETE_TIME = 3600  # 1 soat

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(ENCODE_DIR, exist_ok=True)

app = Client(
    name="user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION
)

user_cache = {}

# ================= HELPERS =================

async def download_progress(current, total, message, start):
    if total == 0:
        return

    now = time.time()
    diff = now - start
    if diff == 0:
        return

    mb_done = current / 1024 / 1024
    if int(mb_done) % CHUNK_MB != 0:
        return

    percent = current * 100 / total
    speed = mb_done / diff

    text = (
        "📥 Yuklab olinmoqda...\n\n"
        f"📦 {mb_done:.1f} MB / {total/1024/1024:.1f} MB\n"
        f"⚡ {speed:.2f} MB/s\n"
        f"⏳ {percent:.1f}%"
    )

    try:
        await message.edit(text)
    except:
        pass


async def encode_video(input_path, output_path, scale, message):
    # video duration
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", input_path
    ]
    duration = float(subprocess.check_output(cmd).decode().strip())

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        *scale.split(),
        "-preset", "ultrafast",
        "-movflags", "+faststart",
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stderr=asyncio.subprocess.PIPE
    )

    last_percent = 0

    while True:
        line = await process.stderr.readline()
        if not line:
            break

        line = line.decode(errors="ignore")
        if "time=" in line:
            t = line.split("time=")[1].split(" ")[0]
            h, m, s = t.split(":")
            seconds = int(h) * 3600 + int(m) * 60 + float(s)
            percent = min(int(seconds * 100 / duration), 100)

            if percent - last_percent >= 5:
                last_percent = percent
                try:
                    await message.edit(f"🎬 Encode qilinmoqda...\n\n⏳ {percent}%")
                except:
                    pass

    await process.wait()


async def auto_delete(*files):
    await asyncio.sleep(AUTO_DELETE_TIME)
    for f in files:
        if f and os.path.exists(f):
            os.remove(f)

# ================= BUTTONS =================

encode_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("240p", callback_data="240")],
    [InlineKeyboardButton("360p", callback_data="360")],
    [InlineKeyboardButton("480p", callback_data="480")],
    [InlineKeyboardButton("Ultra Fast", callback_data="ultra")]
])

# ================= HANDLERS =================

@app.on_message(filters.video | filters.document)
async def video_handler(client, message):
    user_cache[message.chat.id] = message

    await message.reply(
        "🎥 Video qabul qilindi.\n\nQayta ishlashni xohlaysizmi?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ha", callback_data="yes"),
                InlineKeyboardButton("❌ Yo‘q", callback_data="no")
            ]
        ])
    )


@app.on_callback_query(filters.regex("^yes$"))
async def ask_encode(client, query):
    await query.message.edit(
        "⚙ Encode sifatini tanlang:",
        reply_markup=encode_buttons
    )


@app.on_callback_query(filters.regex("^(240|360|480|ultra)$"))
async def start_encode(client, query):
    msg = user_cache.get(query.message.chat.id)
    if not msg:
        return

    start_time = time.time()
    status = await query.message.edit("📥 Yuklab olinmoqda...")

    file_path = await msg.download(
        file_name=f"{DOWNLOAD_DIR}/{msg.id}",
        progress=download_progress,
        progress_args=(status, start_time)
    )

    if query.data == "240":
        scale = "-vf scale=426:240"
    elif query.data == "360":
        scale = "-vf scale=640:360"
    elif query.data == "480":
        scale = "-vf scale=854:480"
    else:
        scale = "-crf 35"

    out_path = f"{ENCODE_DIR}/{os.path.basename(file_path)}.mp4"

    await status.edit("🎬 Encode boshlanmoqda...")
    await encode_video(file_path, out_path, scale, status)

    await status.edit("📤 Telegramga yuborilmoqda...")
    await msg.reply_video(out_path)

    asyncio.create_task(auto_delete(file_path, out_path))


@app.on_callback_query(filters.regex("^no$"))
async def cancel(query):
    await query.message.edit("❌ Bekor qilindi.")

# ================= RUN =================

app.run()
