import os
import asyncio
import math
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

================== CONFIG ==================

API_ID = int(os.getenv("API_ID")) API_HASH = os.getenv("API_HASH") SESSION = os.getenv("SESSION", "user") DOWNLOAD_DIR = "downloads" ENCODE_DIR = "encoded" CHUNK_MB = 5

os.makedirs(DOWNLOAD_DIR, exist_ok=True) os.makedirs(ENCODE_DIR, exist_ok=True)

app = Client(SESSION, api_id=API_ID, api_hash=API_HASH)

================== HELPERS ==================

async def progress(current, total, message, start, prefix): percent = current * 100 / total elapsed = time.time() - start speed = current / elapsed if elapsed > 0 else 0 text = ( f"{prefix}\n" f"📦 {current/1024/1024:.1f} MB / {total/1024/1024:.1f} MB\n" f"⚡ {speed/1024/1024:.2f} MB/s\n" f"⏳ {percent:.1f}%" ) try: await message.edit(text) except: pass

async def auto_delete(*paths, delay=3600): await asyncio.sleep(delay) for p in paths: if p and os.path.exists(p): os.remove(p)

async def encode(input_path, output_path, preset, message): cmd = f"ffmpeg -y -i '{input_path}' {preset} '{output_path}'" process = await asyncio.create_subprocess_shell(cmd) while process.returncode is None: try: await message.edit("🎬 Encode qilinmoqda...") except: pass await asyncio.sleep(5) await process.wait()

================== BUTTONS ==================

encode_buttons = InlineKeyboardMarkup([ [InlineKeyboardButton("240p", callback_data="240")], [InlineKeyboardButton("360p", callback_data="360")], [InlineKeyboardButton("480p", callback_data="480")], [InlineKeyboardButton("Ultra Fast", callback_data="ultra")] ])

================== HANDLERS ==================

@app.on_message(filters.video | filters.document) async def on_video(client, message): if not (message.video or message.document): return

await message.reply(
    "🎥 Video qabul qilindi. Qayta ishlashni xohlaysizmi?",
    reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha", callback_data="yes")],
        [InlineKeyboardButton("❌ Yo'q", callback_data="no")]
    ])
)
client.storage = message

@app.on_callback_query(filters.regex("yes")) async def ask_encode(client, query): await query.message.edit("⚙ Encode turini tanlang:", reply_markup=encode_buttons)

@app.on_callback_query(filters.regex("240|360|480|ultra")) async def do_encode(client, query): msg = client.storage start = time.time()

progress_msg = await query.message.edit("📥 Yuklanmoqda...")

file_path = await msg.download(
    file_name=f"{DOWNLOAD_DIR}/{msg.id}",
    progress=progress,
    progress_args=(progress_msg, start, "📥 Yuklab olinmoqda")
)

if query.data == "240":
    preset = "-vf scale=426:240 -preset veryfast"
elif query.data == "360":
    preset = "-vf scale=640:360 -preset veryfast"
elif query.data == "480":
    preset = "-vf scale=854:480 -preset veryfast"
else:
    preset = "-preset ultrafast -crf 35"

out_path = f"{ENCODE_DIR}/{os.path.basename(file_path)}.mp4"

encode_msg = await query.message.edit("🎬 Encode boshlanmoqda...")
await encode(file_path, out_path, preset, encode_msg)

await encode_msg.edit("📤 Telegramga yuborilmoqda...")
await msg.reply_video(out_path)

asyncio.create_task(auto_delete(file_path, out_path, delay=3600))

@app.on_callback_query(filters.regex("no")) async def cancel(query): await query.message.edit("❌ Bekor qilindi")

================== RUN ==================

app.run()
