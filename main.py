import os
import asyncio
import math
import shutil
import subprocess
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

BASE_DIR = "videos"
os.makedirs(BASE_DIR, exist_ok=True)

# ================= KEYBOARDS =================

confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Qayta ishlash", callback_data="process"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    ]
])

quality_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="240p", callback_data="q_240"),
        InlineKeyboardButton(text="360p", callback_data="q_360"),
        InlineKeyboardButton(text="480p", callback_data="q_480"),
    ],
    [
        InlineKeyboardButton(text="⚡ ULTRAFAST", callback_data="q_fast")
    ]
])

# ================= HELPERS =================

async def download_with_progress(message: Message, file_id: str, path: str):
    file = await bot.get_file(file_id)
    total = file.file_size
    chunk = 5 * 1024 * 1024  # 5MB

    downloaded = 0
    status = await message.answer("📥 Yuklanmoqda: 0 MB")

    async with bot.session.get(
        f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    ) as resp:
        with open(path, "wb") as f:
            async for data in resp.content.iter_chunked(chunk):
                f.write(data)
                downloaded += len(data)
                mb_done = downloaded // (1024 * 1024)
                mb_total = total // (1024 * 1024)
                await status.edit_text(
                    f"📥 Yuklanmoqda: {mb_done} / {mb_total} MB"
                )

    return status


async def encode_video(input_path, output_path, scale=None, preset="ultrafast", status_msg=None):
    cmd = ["ffmpeg", "-y", "-i", input_path]

    if scale:
        cmd += ["-vf", f"scale=-2:{scale}"]

    cmd += ["-preset", preset, output_path]

    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, universal_newlines=True
    )

    duration = None

    for line in process.stderr:
        if "Duration" in line:
            time_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = time_str.split(":")
            duration = int(float(h)) * 3600 + int(float(m)) * 60 + float(s)

        if "time=" in line and duration and status_msg:
            t = line.split("time=")[1].split(" ")[0]
            h, m, s = t.split(":")
            cur = int(float(h)) * 3600 + int(float(m)) * 60 + float(s)
            percent = min(100, int((cur / duration) * 100))
            await status_msg.edit_text(f"⚙️ Encode: {percent}%")

    process.wait()


def cleanup(*paths):
    for p in paths:
        if os.path.exists(p):
            os.remove(p)

# ================= HANDLERS =================

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "👋 <b>Xush kelibsiz!</b>\n\n"
        "📹 Videoni yuboring (oddiy / forward / document)\n"
        "Men uni qayta ishlab beraman."
    )


@dp.message(F.video | F.document)
async def handle_video(msg: Message):
    await msg.answer(
        "🎬 Video qabul qilindi.\nQayta ishlaymi?",
        reply_markup=confirm_kb
    )
    dp["last_msg"] = msg


@dp.callback_query(F.data == "cancel")
async def cancel(cb: CallbackQuery):
    await cb.message.edit_text("❌ Bekor qilindi")


@dp.callback_query(F.data == "process")
async def process(cb: CallbackQuery):
    msg: Message = dp["last_msg"]

    file = msg.video or msg.document
    file_id = file.file_id

    uid = msg.from_user.id
    in_path = f"{BASE_DIR}/{uid}_input.mp4"

    status = await download_with_progress(msg, file_id, in_path)

    await status.edit_text("✅ Yuklab bo‘ldi. Sifatni tanlang:", reply_markup=quality_kb)

    dp["input"] = in_path
    dp["status"] = status


@dp.callback_query(F.data.startswith("q_"))
async def quality(cb: CallbackQuery):
    in_path = dp["input"]
    status = dp["status"]

    uid = cb.from_user.id
    out_path = f"{BASE_DIR}/{uid}_out.mp4"

    q = cb.data

    await status.edit_text("⚙️ Encode boshlandi...")

    if q == "q_240":
        await encode_video(in_path, out_path, scale=240, status_msg=status)
    elif q == "q_360":
        await encode_video(in_path, out_path, scale=360, status_msg=status)
    elif q == "q_480":
        await encode_video(in_path, out_path, scale=480, status_msg=status)
    else:
        await encode_video(in_path, out_path, preset="ultrafast", status_msg=status)

    await cb.message.answer_video(
        video=open(out_path, "rb"),
        caption="✅ Tayyor!"
    )

    cleanup(in_path, out_path)
    await status.delete()

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
