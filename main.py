import os
import logging
import subprocess
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

WORKDIR = "videos"
os.makedirs(WORKDIR, exist_ok=True)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 Videoni yuboring.\nMen uni qayta encode qilib beraman."
    )

# video qabul qilish (oddiy + forward + document)
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    video = None

    if msg.video:
        video = msg.video
    elif msg.document and msg.document.mime_type.startswith("video"):
        video = msg.document

    if not video:
        await msg.reply_text("❌ Video aniqlanmadi.")
        return

    context.user_data.clear()
    context.user_data["file_id"] = video.file_id
    context.user_data["size"] = video.file_size
    context.user_data["uid"] = video.file_unique_id

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Qayta ishlash", callback_data="process"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
        ]
    ])

    await msg.reply_text(
        "🎬 Video qabul qilindi.\nQayta ishlaymizmi?",
        reply_markup=kb
    )

# tugmalar
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    if data == "process":
        await download_video(query, context)
        return

    if data.startswith("enc_"):
        res = data.split("_")[1]
        await encode_video(query, context, res)

# REAL download progress (5MB)
async def download_video(query, context):
    file_id = context.user_data["file_id"]
    size = context.user_data["size"]
    uid = context.user_data["uid"]

    in_path = f"{WORKDIR}/{uid}_in.mp4"
    context.user_data["in_path"] = in_path

    msg = await query.edit_message_text("📥 Yuklab olinmoqda...")

    file = await context.bot.get_file(file_id)
    downloaded = 0
    last_report = 0

    async def progress(current, total):
        nonlocal last_report
        if current - last_report >= 5 * 1024 * 1024:
            last_report = current
            await msg.edit_text(
                f"📥 Yuklanmoqda: {current//1024//1024}MB / {total//1024//1024}MB"
            )

    await file.download_to_drive(
        custom_path=in_path,
        read_timeout=120,
        write_timeout=120,
        block_size=1024 * 1024,
        progress=progress
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("240p ⚡", callback_data="enc_240")],
        [InlineKeyboardButton("360p ⚡", callback_data="enc_360")],
        [InlineKeyboardButton("480p ⚡", callback_data="enc_480")]
    ])

    await msg.edit_text(
        "✅ Video yuklandi.\nSifatni tanlang:",
        reply_markup=kb
    )

# encode (ultrafast)
async def encode_video(query, context, res):
    in_path = context.user_data["in_path"]
    uid = context.user_data["uid"]
    out_path = f"{WORKDIR}/{uid}_{res}p.mp4"

    await query.edit_message_text("⚙️ Encode qilinyapti... ⏳")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", in_path,
        "-vf", f"scale=-2:{res}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        out_path
    ])

    await query.edit_message_text("📤 Video yuborilmoqda...")

    await query.message.reply_video(video=open(out_path, "rb"))

    os.remove(in_path)
    os.remove(out_path)
    context.user_data.clear()

# main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.VIDEO,
            video_handler
        )
    )
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
