import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import ffmpeg
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# /start handler
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Videoni yuboring va men uni qayta ishlab beraman")

# Video handler
@dp.message_handler(content_types=['video', 'document'])
async def handle_video(message: types.Message):
    video = message.video or message.document
    file_id = video.file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    download_path = f"downloads/{video.file_name}"
    os.makedirs('downloads', exist_ok=True)

    # Progress xabar
    progress_msg = await message.reply(f"Yuklanmoqda... 0%")
    await bot.download_file(file_path, download_path)
    await progress_msg.edit_text(f"🎬 Video qabul qilindi!")

    # Tugmalar
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('240p'), KeyboardButton('360p'), KeyboardButton('480p'))
    await message.reply("Sifatni tanlang", reply_markup=keyboard)

# Sifat handler
@dp.message_handler(lambda message: message.text in ['240p', '360p', '480p'])
async def encode_video(message: types.Message):
    quality = message.text
    input_file = max([os.path.join('downloads', f) for f in os.listdir('downloads')], key=os.path.getctime)
    output_file = f"downloads/encoded_{quality}_{os.path.basename(input_file)}"

    await message.reply(f"Video {quality} sifatga tayyorlanmoqda...")
    stream = ffmpeg.input(input_file)
    stream = ffmpeg.output(stream, output_file, **{'s': quality, 'c:v': 'libx264'})
    ffmpeg.run(stream)

    await message.reply_document(open(output_file, 'rb'), caption=f"Video {quality} sifatda tayyor")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
