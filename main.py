import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import ffmpeg
from telethon import TelegramClient

# ----------------------
# Environment variables
# ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = TelegramClient("anon_session", API_ID, API_HASH)

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

async def send_progress(msg, current, total, step=5):
    if current % step == 0 or current >= total:
        await msg.edit_text(f"Yuklanmoqda: {current} MB / {total} MB")

# ----------------------
# Handlers
# ----------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Videoni yuboring va men uni qayta ishlab, link beraman!")

@dp.message()
async def video_handler(message: types.Message):
    file = message.document or message.video
    if not file:
        return
    file_size_mb = file.file_size / (1024*1024)
    if file_size_mb > 10240:  # maksimal 10GB
        await message.reply("Kechirasiz, video juda katta!")
        return
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

    # Faylni real progress bilan yuklash
    CHUNK_SIZE = 5*1024*1024  # 5 MB
    total_size = file_info.file_size
    downloaded = 0
    with open(local_path, "wb") as f:
        stream = await bot.download_file(file_info.file_path)
        while True:
            chunk = await stream.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            await send_progress(msg, downloaded//(1024*1024), total_size//(1024*1024), step=5)

    await msg.edit_text(f"Yuklab olindi: {os.path.getsize(local_path)/(1024*1024):.2f} MB")
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

    # Faqat link berish (Telegramga qayta yubormaydi)
    link = f"/tmp/{output_name}"  # foydalanuvchi keyin o‘zi yuklab oladi
    await callback.message.edit_text(f"Videoni tayyorladim! Yuklab olish uchun fayl serverda:\n{link}\nBu fayl 8 soatdan keyin o‘chiriladi.")

    # Server fayllarini avtomatik o‘chirish (8 soatdan keyin)
    asyncio.create_task(auto_delete_files([input_path, output_path], delay=8*3600))

async def auto_delete_files(files, delay):
    await asyncio.sleep(delay)
    for f in files:
        if os.path.exists(f):
            os.remove(f)

# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
