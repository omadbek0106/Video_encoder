import os
import logging
import asyncio
import requests
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "/tmp"
MAX_SIZE = 1024 * 1024 * 1024  # 1GB


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Videoni yuboring va men uni qayta ishlayman.")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    size = video.file_size

    if size > MAX_SIZE:
        await update.message.reply_text("❌ Video 1GB dan katta. Telegram bot limiti sabab yuklab bo‘lmaydi.")
        return

    await update.message.reply_text("📥 Video yuklanmoqda...")

    file = await context.bot.get_file(video.file_id)
    file_url = file.file_path
    full_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_url}"

    input_path = os.path.join(DOWNLOAD_DIR, f"{video.file_id}.mp4")

    try:
        r = requests.get(full_url, stream=True, timeout=60)
        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(input_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

        context.user_data["video_path"] = input_path

    except Exception as e:
        logging.error(f"Download error: {e}")
        await update.message.reply_text("❌ Video yuklab bo‘lmadi.")
        return

    keyboard = [
        [
            InlineKeyboardButton("240p ⚡", callback_data="240"),
            InlineKeyboardButton("360p", callback_data="360"),
            InlineKeyboardButton("480p", callback_data="480"),
        ]
    ]

    await update.message.reply_text(
        "📊 Qaysi sifatda chiqarsin?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def encode_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    resolution = query.data
    input_path = context.user_data.get("video_path")

    if not input_path:
        await query.edit_message_text("❌ Video topilmadi.")
        return

    output_path = input_path.replace(".mp4", f"_{resolution}p.mp4")

    await query.edit_message_text(f"⚙️ {resolution}p ga encode qilinmoqda...")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf", f"scale=-2:{resolution}",
        "-preset", "ultrafast",
        "-c:v", "libx264",
        "-crf", "32",
        "-c:a", "aac",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        logging.error(f"FFmpeg error: {e}")
        await query.edit_message_text("❌ Encode qilishda xato.")
        return

    await query.edit_message_text("📤 Telegramga yuklanmoqda...")

    try:
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=open(output_path, "rb"),
        )
    except Exception as e:
        logging.error(f"Upload error: {e}")
        await query.edit_message_text("❌ Video yuborib bo‘lmadi.")
        return

    os.remove(input_path)
    os.remove(output_path)


def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(encode_video))

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
