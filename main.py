import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions
from aiogram.filters import Command
import aiohttp
import ffmpeg

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Progress update helper
async def send_progress(chat_id, message_id, downloaded, total):
    percent = int(downloaded / total * 100)
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📥 Yuklanmoqda: {downloaded}MB / {total}MB ({percent}%)"
        )
    except exceptions.MessageNotModified:
        pass

# Start command
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🎬 Videoni yuboring va men uni qayta ishlab beraman. Forward videolar ham ishlaydi!")

# Video or document handler
@dp.message(lambda m: m.video or m.document)
async def video_handler(message: types.Message):
    file_size = message.video.file_size if message.video else message.document.file_size
    if file_size > 1_100_000_000:  # ~1GB limit
        await message.answer("❌ Fayl juda katta! Maks 1GB.")
        return

    # Tasdiqlash
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Ha, qayta ishlash", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ Yo'q, bekor qil", callback_data="confirm_no")]
    ])
    await message.answer("📌 Siz video yubordingiz. Qayta ishlashni xohlaysizmi?", reply_markup=confirm_kb)
    dp.current_file = message  # Saqlaymiz keyingi jarayon uchun

# Callback query
@dp.callback_query()
async def cb_handler(callback: types.CallbackQuery):
    data = callback.data
    message = dp.current_file

    if data == "confirm_no":
        await callback.message.edit_text("❌ Qayta ishlash bekor qilindi.")
        return

    if data == "confirm_yes":
        await callback.message.edit_text("📥 Video yuklanmoqda...")
        file_id = message.video.file_id if message.video else message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        dest_path = f"./{file.file_unique_id}.mp4"

        # Download with progress
        async with aiohttp.ClientSession() as session:
            tg_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            async with session.get(tg_url) as resp:
                total = int(resp.headers.get("Content-Length", 0)) // (1024*1024)  # MB
                downloaded = 0
                chunk_size = 1024 * 1024 * 5  # 5MB
                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk) // (1024*1024)
                        await send_progress(callback.message.chat.id, callback.message.message_id, downloaded, total)

        # Format selection
        format_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("240p", callback_data="encode_240"),
             InlineKeyboardButton("360p", callback_data="encode_360")],
            [InlineKeyboardButton("480p", callback_data="encode_480"),
             InlineKeyboardButton("Ultra Fast", callback_data="encode_fast")]
        ])
        await callback.message.edit_text("🎞 Videoni encode qilish formatini tanlang:", reply_markup=format_kb)
        dp.downloaded_file = dest_path

    if data.startswith("encode_"):
        format_choice = data.split("_")[1]
        input_file = dp.downloaded_file
        output_file = f"./encoded_{format_choice}_{os.path.basename(input_file)}"

        await callback.message.edit_text(f"🔧 Encode jarayoni boshlandi: {format_choice}...")
        if format_choice == "fast":
            stream = ffmpeg.input(input_file).output(output_file, preset="ultrafast").overwrite_output()
        else:
            resolution = format_choice + "p"
            stream = ffmpeg.input(input_file).output(output_file, vf=f"scale=-2:{format_choice}").overwrite_output()
        ffmpeg.run(stream)

        await callback.message.answer_document(InputFile(output_file), caption=f"✅ Video tayyor! Format: {format_choice}")
        os.remove(input_file)
        os.remove(output_file)
        await callback.message.edit_text("🎬 Encode tugadi!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
