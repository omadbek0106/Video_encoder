import os
import asyncio
import time
import math
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== CONFIG ==================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")  # session string

DOWNLOAD_DIR = "downloads"
ENCODE_DIR = "encoded"
AUTO_DELETE = 3600  # 1 hour

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(ENCODE_DIR, exist_ok=True)

app = Client(
    name="user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION
)

# ================== HELPERS ==================
async def download_progress(current, total, message, start):
    percent = current * 100 / total
    elapsed = time.time() - start
    speed = current / elapsed if elapsed > 0 else 0

    text = (
        "📥 Yuklab olinmoqda...\n"
        f"📦 {current/1024/1024:.1f} MB / {total/1024/1024:.1f} MB\n"
        f"⚡ {speed/1024/1024:.2f} MB/s\n"
        f"⏳ {percent:.1f}%"
    )
    try:
        await message.edit(text)
    except:
        pass


async def auto_delete(*paths, delay=AUTO_DELETE):
    await asyncio.sleep(delay)
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)


async def encode_video(input_path, output_path, ffmpeg_args, message):
    cmd = f"ffmpeg -y -i '{input_path}' {ffmpeg_args} '{output_path}'"
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    percent = 0
    while process.returncode is None:
        percent = min(percent + 5, 100)
        try:
            await message.edit(f"🎬 Encode qilinmoqda... {percent}%")
        except:
            pass
        await asyncio.sleep(2)

    await process.wait()

# ================== BUTTONS ==================
ENCODE_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("240p", callback_data="240")],
    [InlineKeyboardButton("360p", callback_data="360")],
    [InlineKeyboardButton("480p", callback_data="480")],
    [InlineKeyboardButton("Ultra Fast", callback_data="ultra")]
])

# ================== HANDLERS ==================
@app.on_message(filters.video | filters.document)
async def on_video(client, message):
    message._cached_video = message
    await message.reply(
        "🎥 Video qabul qilindi. Qayta ishlashni xohlaysizmi?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ha", callback_data="yes")],
            [InlineKeyboardButton("❌ Yo‘q", callback_data="no")]
        ])
    )


@app.on_callback_query(filters.regex("yes"))
async def choose_encode(client, query):
    await query.message.edit(
        "⚙ Encode turini tanlang:",
        reply_markup=ENCODE_BUTTONS
    )


@app.on_callback_query(filters.regex("240|360|480|ultra"))
async def process_encode(client, query):
    msg = query.message.reply_to_message
    start = time.time()

    progress_msg = await query.message.edit("📥 Yuklab olinmoqda...")

    file_path = await msg.download(
        file_name=f"{DOWNLOAD_DIR}/{msg.id}",
        progress=download_progress,
        progress_args=(progress_msg, start)
    )

    if query.data == "240":
        ffmpeg_args = "-vf scale=426:240 -preset veryfast"
    elif query.data == "360":
        ffmpeg_args = "-vf scale=640:360 -preset veryfast"
    elif query.data == "480":
        ffmpeg_args = "-vf scale=854:480 -preset veryfast"
    else:
        ffmpeg_args = "-preset ultrafast -crf 35"

    output_path = f"{ENCODE_DIR}/{os.path.basename(file_path)}.mp4"

    encode_msg = await progress_msg.edit("🎬 Encode boshlanmoqda...")
    await encode_video(file_path, output_path, ffmpeg_args, encode_msg)

    await encode_msg.edit("📤 Telegramga yuborilmoqda...")
    await msg.reply_video(output_path)

    asyncio.create_task(auto_delete(file_path, output_path))


@app.on_callback_query(filters.regex("no"))
async def cancel(query):
    await query.message.edit("❌ Bekor qilindi")

# ================== RUN ==================
if __name__ == "__main__":
    app.run()
