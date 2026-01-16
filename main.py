import os
import asyncio
from telethon import TelegramClient, events
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg
import aiofiles

# ----------------------
# Environment variables
# ----------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "anon_session")  # Telethon session fayl nomi

# ----------------------
# Telegram client
# ----------------------
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ----------------------
# Inline keyboards
# ----------------------
def process_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Ha", callback_data="process_yes"),
             InlineKeyboardButton("Yo'q", callback_data="process_no")]
        ]
    )

def encode_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("240p", callback_data="240")],
            [InlineKeyboardButton("360p", callback_data="360")],
            [InlineKeyboardButton("480p", callback_data="480")],
            [InlineKeyboardButton("Ultra Fast", callback_data="ultrafast")]
        ]
    )

# ----------------------
# Helper functions
# ----------------------
async def encode_video(input_path, output_path, resolution=None, ultrafast=False):
    stream = ffmpeg.input(input_path)
    if ultrafast:
        stream = ffmpeg.output(stream, output_path, preset='ultrafast')
    else:
        stream = ffmpeg.output(stream, output_path, vf=f"scale=-2:{resolution}", preset='ultrafast')
    ffmpeg.run(stream, overwrite_output=True)

# ----------------------
# Event handlers
# ----------------------
@client.on(events.NewMessage)
async def handler(event):
    if not event.message.video and not event.message.document:
        return

    file_size_mb = event.message.file.size / (1024 * 1024)
    if file_size_mb > 2048:  # max 2GB limit
        await event.reply("Kechirasiz, video juda katta (>2GB)!")
        return

    # Qayta ishlashni so‘rash
    await event.reply(f"Videoni qayta ishlashni xohlaysizmi?\nHajmi: {file_size_mb:.2f} MB", buttons=process_keyboard())

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')

    # Qayta ishlash bekor qilindi
    if data == "process_no":
        await event.edit("Videoni qayta ishlash bekor qilindi.")
        return

    # Video faylini yuklash
    message = await event.get_message()
    reply = message.reply_to_msg
    input_path = f"/tmp/{reply.file.name if reply.file else 'video.mp4'}"

    # Real download progress 5MB
    async with aiofiles.open(input_path, 'wb') as f:
        size_downloaded = 0
        async for chunk in client.iter_download(reply.media, buffer_size=5*1024*1024):
            await f.write(chunk)
            size_downloaded += len(chunk)
            await event.edit(f"Video yuklanmoqda: {size_downloaded/(1024*1024):.2f} MB")

    # Encode tugmalari
    await event.edit("Videoni qaysi formatga encode qilamiz?", buttons=encode_keyboard())

@client.on(events.CallbackQuery)
async def encode_callback(event):
    data = event.data.decode('utf-8')
    message = await event.get_message()
    reply = message.reply_to_msg
    input_path = f"/tmp/{reply.file.name if reply.file else 'video.mp4'}"
    output_name = f"encoded_{data}.mp4"
    output_path = f"/tmp/{output_name}"

    if data == "ultrafast":
        await event.edit("Ultra Fast encode qilinmoqda...")
        await encode_video(input_path, output_path, ultrafast=True)
    else:
        resolution = int(data)
        await event.edit(f"{resolution}p ga encode qilinmoqda...")
        await encode_video(input_path, output_path, resolution=resolution)

    # Faqat link berish
    await event.edit(f"Videoni tayyor! Fayl linki:\nfile://{output_path}")

    # Server fayllarini o‘chirish (8 soatdan keyin)
    asyncio.create_task(auto_delete(input_path, output_path))

async def auto_delete(input_path, output_path):
    await asyncio.sleep(8*3600)
    if os.path.exists(input_path):
        os.remove(input_path)
    if os.path.exists(output_path):
        os.remove(output_path)

# ----------------------
# Main
# ----------------------
async def main():
    await client.start()
    print("Bot ishga tushdi...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
