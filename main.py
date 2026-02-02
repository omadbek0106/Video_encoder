import os
import time
import asyncio
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

app = Client(
    "encoder_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

DOWNLOAD = "downloads/"
OUTPUT = "outputs/"

os.makedirs(DOWNLOAD, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

# ===== PROGRESS FUNCTION =====
async def progress(current, total, message, start, text):
    now = time.time()
    diff = now - start
    if diff < 1:
        return

    percent = current * 100 / total
    speed = current / diff / 1024 / 1024

    await message.edit(
        f"{text}\n\n"
        f"📦 {current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB\n"
        f"⚡ {speed:.2f} MB/s\n"
        f"⏳ {percent:.2f}%"
    )

# ===== AUTO DELETE =====
async def auto_delete(*files):
    await asyncio.sleep(3600)
    for f in files:
        if os.path.exists(f):
            os.remove(f)

# ===== START =====
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "🎬 Video Encoder UserBot ishga tayyor!\n\n"
        "Menga video yuboring."
    )

# ===== VIDEO HANDLER =====
@app.on_message(filters.video | filters.document)
async def video_received(client, message):

    await message.reply(
        "🎥 Video qabul qilindi!\nQayta ishlashni xohlaysizmi?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ha", callback_data="yes"),
                InlineKeyboardButton("❌ Yo‘q", callback_data="no")
            ]
        ])
    )

    app.last_video = message


# ===== CALLBACK =====
@app.on_callback_query()
async def callbacks(client, query):

    data = query.data

    if data == "no":
        await query.message.edit("❌ Bekor qilindi")
        return

    if data == "yes":
        await query.message.edit(
            "Formatni tanlang:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("240p", callback_data="240")],
                [InlineKeyboardButton("360p", callback_data="360")],
                [InlineKeyboardButton("480p", callback_data="480")],
                [InlineKeyboardButton("Ultra Fast", callback_data="ultra")]
            ])
        )
        return

    await encode_process(client, query)


# ===== ENCODE PROCESS =====
async def encode_process(client, query):

    msg = app.last_video

    start = time.time()

    status = await query.message.edit("📥 Yuklab olinmoqda...")

    file = await msg.download(
        file_name=DOWNLOAD,
        progress=progress,
        progress_args=(status, start, "📥 Yuklanmoqda")
    )

    out = OUTPUT + os.path.basename(file) + ".mp4"

    preset = query.data

    await status.edit("🎬 Encode boshlanmoqda...")

    if preset == "ultra":
        cmd = f"ffmpeg -y -i \"{file}\" -preset ultrafast \"{out}\""
    else:
        scales = {
            "240": "426:240",
            "360": "640:360",
            "480": "854:480"
        }
        cmd = f"ffmpeg -y -i \"{file}\" -vf scale={scales[preset]} -preset veryfast \"{out}\""

    process = await asyncio.create_subprocess_shell(cmd)

    # simple encode progress loop
    for i in range(0, 101, 5):
        await status.edit(f"🎞 Encode qilinmoqda...\n⏳ {i}%")
        await asyncio.sleep(2)

    await process.wait()

    await status.edit("📤 Telegramga yuborilmoqda...")

    await msg.reply_video(out, caption="✅ Encode qilingan video")

    asyncio.create_task(auto_delete(file, out))

    await status.edit("🎉 Tayyor!")


print("UserBot ishga tushmoqda...")
app.run()
