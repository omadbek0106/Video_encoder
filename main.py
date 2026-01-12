import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import ffmpeg

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

QUALITY_OPTIONS = {
    "240p ⚡": 240,
    "360p ⚡": 360,
    "480p ⚡": 480
}

USER_VIDEO = {}


def quality_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for q in QUALITY_OPTIONS:
        kb.add(InlineKeyboardButton(q, callback_data=f"q_{q}"))
    return kb


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🎬 Videoni yuboring va men uni tezkor formatlarda qayta kodlab beraman!")


@dp.message_handler(content_types=["video", "document"])
async def handle_video(message: types.Message):
    if message.video:
        file = message.video
    elif message.document and message.document.mime_type.startswith("video"):
        file = message.document
    else:
        return

    msg = await message.answer("📥 Video yuklab olinmoqda...")

    file_info = await bot.get_file(file.file_id)
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{file.file_id}.mp4"

    await bot.download_file(file_info.file_path, file_path)

    USER_VIDEO[message.from_user.id] = file_path

    await msg.edit_text("✅ Yuklandi!\n\n🎚 Kerakli sifatni tanlang:", reply_markup=quality_keyboard())


@dp.callback_query_handler(lambda c: c.data.startswith("q_"))
async def process_quality(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    quality = callback.data.replace("q_", "")

    if user_id not in USER_VIDEO:
        await callback.answer("Video topilmadi", show_alert=True)
        return

    input_path = USER_VIDEO[user_id]
    height = QUALITY_OPTIONS[quality]

    output = f"{quality.replace(' ','_')}_{user_id}.mp4"

    await callback.message.edit_text("⚙️ Video kodlanmoqda, kuting...")

    try:
        (
            ffmpeg
            .input(input_path)
            .output(output, vf=f"scale=-2:{height}", preset="ultrafast", crf=28)
            .run(overwrite_output=True)
        )

        await bot.send_video(user_id, open(output, "rb"))
    except Exception as e:
        await bot.send_message(user_id, f"❌ Xatolik: {e}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output):
            os.remove(output)
        USER_VIDEO.pop(user_id, None)


if __name__ == "__main__":
    executor.start_polling(dp)
