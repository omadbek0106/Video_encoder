import os
import logging
import subprocess

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= LOG =================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yo‘q (Railway Variables)")

DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "outputs"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom!\n🎬 Videoni yuboring."
    )

# ================= VIDEO QABUL =================
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    context.user_data.clear()

    context.user_data["file_id"] = video.file_id
    context.user_data["file_size"] = video.file_size

    size_mb = video.file_size / (1024 * 1024)

    keyboard = [
        [
            InlineKeyboardButton("▶️ Qayta ishlash", callback_data="process"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
        ]
    ]

    await update.message.reply_text(
        f"🎬 Video qabul qilindi\n📦 Hajmi: {size_mb:.1f} MB\n\nNima qilamiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= QAROR =================
async def decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    if query.data == "process":
        await query.edit_message_text("⏬ Yuklab olinmoqda...")
        await download_video(query, context)

# ================= YUKLASH =================
async def download_video(query, context):
    file_id = context.user_data.get("file_id")
    total = context.user_data.get("file_size")

    file = await context.bot.get_file(file_id)
    path = f"{DOWNLOAD_DIR}/{file_id}.mp4"

    downloaded = 0
    last = 0

    async for chunk in file.download_as_bytearray():
        with open(path, "ab") as f:
            f.write(chunk)

        downloaded += len(chunk)
        mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)

        if mb - last >= 10:
            last = mb
            try:
                await query.edit_message_text(
                    f"⏬ Yuklanmoqda...\n{mb:.1f} / {total_mb:.1f} MB"
                )
            except:
                pass

    context.user_data["video_path"] = path

    keyboard = [
        [InlineKeyboardButton("240p ⚡ Juda tez", callback_data="240")],
        [
            InlineKeyboardButton("360p", callback_data="360"),
            InlineKeyboardButton("480p", callback_data="480")
        ]
    ]

    await query.edit_message_text(
        "✅ Yuklab olindi!\n📽 Sifatni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= SIFAT =================
async def quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    input_path = context.user_data.get("video_path")

    if not input_path:
        await query.edit_message_text("❌ Video topilmadi.")
        return

    output = f"{OUTPUT_DIR}/out_{quality}p.mp4"

    await query.edit_message_text(
        f"⚙️ {quality}p encode qilinmoqda..."
    )

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", f"scale=-2:{quality}",
                "-preset", "ultrafast",
                "-c:a", "copy",
                output
            ],
            check=True
        )

        await query.message.reply_video(
            video=open(output, "rb"),
            caption=f"✅ Tayyor ({quality}p)"
        )

    except Exception as e:
        logger.error(e)
        await query.edit_message_text("❌ Xatolik.")

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output):
            os.remove(output)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(decision_callback, pattern="process|cancel"))
    app.add_handler(CallbackQueryHandler(quality_callback, pattern="^(240|360|480)$"))

    logger.info("Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
