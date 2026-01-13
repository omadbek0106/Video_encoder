import os
import logging
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

# ---------- LOG ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------- ENV ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN topilmadi!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DOWNLOAD_DIR = "videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

last_video = {}

# ---------- START ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("🎬 Videoni yuboring va men uni 240p / 360p / 480p qilib beraman.")

# ---------- VIDEO / FILE ----------
@dp.message_handler(content_types=["video", "document"])
async def receive_video(message: types.Message):
    try:
        media = message.video or message.document

        if not media.file_name.endswith((".mp4", ".mkv", ".mov", ".avi")):
            await message.reply("❌ Faqat video fayl yuboring.")
            return

        msg = await message.reply("📥 Video yuklanmoqda...")

        file = await bot.get_file(media.file_id)
        input_path = f"{DOWNLOAD_DIR}/{media.file_name}"

        await bot.download_file(file.file_path, input_path)

        last_video[message.from_user.id] = input_path

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("240p"), KeyboardButton("360p"), KeyboardButton("480p"))

        await msg.edit_text("✅ Video qabul qilindi!\nSifatni tanlang:", reply_markup=kb)
        logging.info(f"Video yuklandi: {input_path}")

    except Exception as e:
        logging.error(f"Download error: {e}")
        await message.reply("❌ Video yuklashda xatolik.")

# ---------- QUALITY ----------
@dp.message_handler(lambda m: m.text in ["240p", "360p", "480p"])
async def encode(message: types.Message):
    try:
        user_id = message.from_user.id

        if user_id not in last_video:
            await message.reply("Avval video yuboring.")
            return

        input_file = last_video[user_id]
        quality = message.text

        scale = {
            "240p": "426:240",
            "360p": "640:360",
            "480p": "854:480"
        }[quality]

        output = input_file.replace(".", f"_{quality}.")

        await message.reply(f"⚙️ {quality} ga encode qilinmoqda...")

        cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-vf", f"scale={scale}",
            "-preset", "ultrafast",
            "-c:v", "libx264",
            "-crf", "30",
            "-c:a", "aac",
            output
        ]

        logging.info("FFmpeg start")
        subprocess.run(cmd, check=True)

        await message.reply_document(open(output, "rb"), caption=f"🎬 {quality} tayyor!")
        logging.info(f"Encode tugadi: {output}")

    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e}")
        await message.reply("❌ Encode paytida xatolik bo‘ldi.")
    except Exception as e:
        logging.error(f"General error: {e}")
        await message.reply("❌ Noma’lum xatolik.")

# ---------- RUN ----------
if __name__ == "__main__":
    logging.info("Bot ishga tushdi")
    executor.start_polling(dp, skip_updates=True)
