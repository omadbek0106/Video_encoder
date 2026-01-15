import os
import asyncio
from aiogram import Bot, types, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import exceptions
from aiogram.filters import Command

TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")  # Agar kerak bo'lsa
API_HASH = os.getenv("API_HASH")  # Agar kerak bo'lsa

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Temporary storage for uploaded videos
uploads = {}

async def start_handler(message: types.Message):
    await message.answer("Videoni yuboring va men uni qayta ishlab beraman!")

@dp.message(Command("start"))
async def start(message: types.Message):
    await start_handler(message)

@dp.message(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT])
async def handle_video(message: types.Message):
    if message.video or (message.document and message.document.mime_type.startswith("video")):
        vid_id = message.video.file_id if message.video else message.document.file_id
        file_size = message.video.file_size if message.video else message.document.file_size

        # Sorash tugmasi
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qayta ishlaymiz", callback_data=f"process:{vid_id}")],
                [InlineKeyboardButton(text="❌ Bekor qilamiz", callback_data=f"cancel:{vid_id}")]
            ]
        )
        uploads[vid_id] = {"file_size": file_size, "message_id": message.message_id, "chat_id": message.chat.id}
        await message.answer(f"🎬 Video qabul qilindi! Hajmi: {round(file_size/1024/1024, 2)} MB\nQayta ishlaymizmi?", reply_markup=markup)
    else:
        await message.answer("Faqat video yoki video document yuboring!")

@dp.callback_query(lambda c: c.data.startswith("process:"))
async def process_video(callback_query: types.CallbackQuery):
    vid_id = callback_query.data.split(":")[1]
    info = uploads.get(vid_id)
    if not info:
        await callback_query.message.answer("Xato: video topilmadi!")
        return

    await callback_query.message.edit_text("📥 Yuklanmoqda... 0 MB / {} MB".format(round(info["file_size"]/1024/1024, 2)))

    # Simulyatsiya qilamiz: real download progress
    downloaded = 0
    while downloaded < info["file_size"]:
        await asyncio.sleep(0.1)  # Har 0.1s progress update
        downloaded += 5*1024*1024  # 5MB
        if downloaded > info["file_size"]:
            downloaded = info["file_size"]
        await callback_query.message.edit_text(
            f"📥 Yuklanmoqda... {round(downloaded/1024/1024,2)} MB / {round(info['file_size']/1024/1024,2)} MB"
        )

    # Tugmalar encode tanlash uchun
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("240p Ultra Fast", callback_data=f"encode:240:{vid_id}")],
            [InlineKeyboardButton("360p Ultra Fast", callback_data=f"encode:360:{vid_id}")],
            [InlineKeyboardButton("480p Ultra Fast", callback_data=f"encode:480:{vid_id}")]
        ]
    )
    await callback_query.message.answer("📥 Yuklash tugadi! Formatni tanlang:", reply_markup=markup)

@dp.callback_query(lambda c: c.data.startswith("cancel:"))
async def cancel_video(callback_query: types.CallbackQuery):
    vid_id = callback_query.data.split(":")[1]
    uploads.pop(vid_id, None)
    await callback_query.message.edit_text("❌ Video bekor qilindi.")

@dp.callback_query(lambda c: c.data.startswith("encode:"))
async def encode_video(callback_query: types.CallbackQuery):
    parts = callback_query.data.split(":")
    resolution = parts[1]
    vid_id = parts[2]

    await callback_query.message.edit_text(f"⚡ Encode boshlandi: {resolution}p Ultra Fast")

    # Simulyatsiya encode jarayoni
    for i in range(0, 101, 5):
        await asyncio.sleep(0.2)
        await callback_query.message.edit_text(f"⚡ Encode: {i}%")

    await callback_query.message.edit_text(f"✅ Encode tugadi: {resolution}p")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    import asyncio
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
