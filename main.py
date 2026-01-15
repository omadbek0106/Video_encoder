import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import aiohttp
import ffmpeg

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Environment variable-da qo'yiladi
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Progress tracking
async def download_video(url, dest):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            size = int(resp.headers.get('Content-Length', 0))
            chunk_size = 1024*1024*5  # 5MB chunk
            with open(dest, 'wb') as f:
                downloaded = 0
                async for chunk in resp.content.iter_chunked(chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = downloaded * 100 // size if size else 0
                    print(f"Downloaded {downloaded // (1024*1024)}MB of {size // (1024*1024)}MB ({percent}%)")

# Start message
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Videoni yuboring va men uni qayta ishlab beraman.")

# Video handler (including forwards)
@dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT])
async def handle_video(message: types.Message):
    video = message.video or message.document
    if not video:
        return
    # Confirm reprocess
    confirm_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    confirm_markup.add(KeyboardButton("Ha, qayta ishlash"), KeyboardButton("Yo, bekor qil"))
    await message.reply("Videoni qayta ishlaymizmi?", reply_markup=confirm_markup)

    @dp.message_handler(lambda m: m.text in ["Ha, qayta ishlash", "Yo, bekor qil"])
    async def confirm_response(confirm_msg: types.Message):
        if confirm_msg.text == "Yo, bekor qil":
            await confirm_msg.reply("Bekor qilindi ✅")
            return
        # Download video
        await confirm_msg.reply("🎬 Video qabul qilindi! Yuklanmoqda...")
        file_path = f"{video.file_id}.mp4"
        file_info = await bot.get_file(video.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        await download_video(url, file_path)

        # Send resolution options
        res_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        res_markup.add("240p", "360p", "480p", "Ultra Fast")
        await confirm_msg.reply("Formatni tanlang:", reply_markup=res_markup)

        @dp.message_handler(lambda m: m.text in ["240p", "360p", "480p", "Ultra Fast"])
        async def encode_video(res_msg: types.Message):
            resolution = res_msg.text
            out_file = f"{video.file_id}_{resolution}.mp4"
            # Encode
            try:
                if resolution != "Ultra Fast":
                    width = int(resolution.replace("p", ""))
                    (
                        ffmpeg
                        .input(file_path)
                        .output(out_file, vf=f"scale=-2:{width}")
                        .run(overwrite_output=True)
                    )
                else:
                    (
                        ffmpeg
                        .input(file_path)
                        .output(out_file, preset="ultrafast")
                        .run(overwrite_output=True)
                    )
                await res_msg.reply_document(open(out_file, 'rb'), caption=f"{resolution} tayyor ✅")
            except Exception as e:
                await res_msg.reply(f"Xato: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
