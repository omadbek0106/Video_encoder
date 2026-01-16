import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
import ffmpeg

# ----------------------
# Environment variables
# ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------------
# Telethon client for large files
# ----------------------
client = TelegramClient('anon_session', API_ID, API_HASH)

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

def encode_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("240p", callback_data="240")],
            [InlineKeyboardButton("360p", callback_data="360")],
            [InlineKeyboardButton("480p", callback_data="480")],
            [InlineKeyboardButton("Ultra Fast", callback_data="ultrafast")]
        ]
    )
    return kb

def process_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Ha", callback_data="process_yes"),
             InlineKeyboardButton("Yo'q", callback_data="process_no")]
        ]
    )
    return kb

# ----------------------
# Handlers
# ----------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Videoni yuboring va men uni qayta ishlab, linkini beraman!")

@dp.message()
async def video_handler(message: types.Message):
    file = message.document or message.video
    if not file:
        return
    file_size_mb = file.file_size / (1024*1024)
    await message.reply(f"Videoni qayta ishlashni xohlaysizmi?\nHajmi: {file_size_mb:.2f} MB", reply_markup=process_keyboard())

@dp.callback_query(lambda c: c.data in ["process_yes", "process_no"])
async def process_decision(callback: types.CallbackQuery):
    if callback.data == "process_no":
        await callback.message.edit_text("Videoni qayta ishlash bekor qilindi.")
        return

    msg = await callback.message.edit_text("Video yuklanmoqda: 0 MB")
    file_msg = callback.message.reply_to_message
    file_id = file_msg.document.file_id if file_msg.document else file_msg.video.file_id
    file_info = await bot.get_file(file_id)
    local_path = f"/tmp/{file_info.file_path.split('/')[-1]}"

    # Telethon bilan user account orqali yuklash
    async with client:
        await client.download_media(file_id, local_path, progress_callback=lambda d, t: asyncio.create_task(msg.edit_text(f"Yuklanmoqda: {d//(1024*1024)}MB / {t//(1024*1024)}MB")))

    await callback.message.answer("Videoni qaysi formatga encode qilamiz?", reply_markup=encode_keyboard())

@dp.callback_query(lambda c: c.data in ["240", "360", "480", "ultrafast"])
async def encode_choice(callback: types.CallbackQuery):
    reply_msg = callback.message.reply_to_message
    input_path = f"/tmp/{reply_msg.document.file_name if reply_msg.document else reply_msg.video.file_name}"
    output_name = f"encoded_{callback.data}.mp4"
    output_path = f"/tmp/{output_name}"

    if callback.data == "ultrafast":
        await callback.message.edit_text("Ultra Fast encode qilinmoqda...")
        await encode_video(input_path, output_path, ultrafast=True)
    else:
        resolution = int(callback.data)
        await callback.message.edit_text(f"{resolution}p ga encode qilinmoqda...")
        await encode_video(input_path, output_path, resolution=resolution)

    # Link berish
    await callback.message.edit_text(f"Videoni tayyor! Faylni yuklab olish uchun link: file://{output_path}")

    # Serverdagi fayllarni o‘chirish
    os.remove(input_path)
    os.remove(output_path)

# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
