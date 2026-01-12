import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import ffmpeg

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Sifat variantlari
QUALITY_OPTIONS = {
    "240p": 240,
    "360p": 360,
    "480p": 480
}

# foydalanuvchi video va sifatni saqlash uchun
USER_VIDEO = {}

def create_quality_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for q in QUALITY_OPTIONS:
        keyboard.add(InlineKeyboardButton(q, callback_data=f"quality_{q}"))
    return keyboard

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.reply("Videoni yuboring va men uni qayta ishlab beraman 🎬")

@dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT])
async def handle_video(message: types.Message):
    if message.video:
        file_id = message.video.file_id
        size = message.video.file_size
        filename = message.video.file_name
    elif message.document and message.document.mime_type.startswith("video"):
        file_id = message.document.file_id
        size = message.document.file_size
        filename = message.document.file_name
    else:
        await message.reply("Iltimos, video yuboring!")
        return

    msg = await message.reply(f"🎬 Video qabul qilindi!\n📥 Yuklab olinmoqda 0 / {size//1024//1024} MB")

    file = await bot.get_file(file_id)
    file_path = file.file_path
    download_path = f"./downloads/{filename}"
    os.makedirs("./downloads", exist_ok=True)

    await bot.download_file(file_path, download_path)

    await msg.edit_text(f"✅ Video yuklab olindi.\nQaysi sifatda encode qilamiz?", reply_markup=create_quality_keyboard())

    USER_VIDEO[message.from_user.id] = download_path

@dp.callback_query_handler(lambda c: c.data.startswith("quality_"))
async def process_quality(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEO:
        await callback_query.answer("Video topilmadi. Iltimos, video yuboring!")
        return

    quality = callback_query.data.split("_")[1]
    input_path = USER_VIDEO[user_id]
    output_dir = "./encoded"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{quality}_{os.path.basename(input_path)}")

    await callback_query.message.edit_text(f"⚡ {quality} da encode qilinmoqda...")

    # ffmpeg encode
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(stream, output_path, vf=f"scale=-2:{QUALITY_OPTIONS[quality]}", preset='ultrafast', c='copy')
    ffmpeg.run(stream, overwrite_output=True)

    await callback_query.message.edit_text(f"📤 Video tayyor! Yuborilmoqda...")
    await bot.send_video(user_id, open(output_path, 'rb'))

    # faylni tozalash
    os.remove(input_path)
    os.remove(output_path)
    USER_VIDEO.pop(user_id)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)# Video_encoder
