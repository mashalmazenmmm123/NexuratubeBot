import os
import logging
import asyncio
import re
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- الإعدادات الأساسية ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FASTSAVER_API_KEY = os.environ.get("FASTSAVER_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

if not BOT_TOKEN or not FASTSAVER_API_KEY:
    raise ValueError("يجب إضافة BOT_TOKEN و FASTSAVER_API_KEY في إعدادات Vercel")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- كود FastSaver API ---
BASE_URL = "https://api.fastsaver.io/v1"

class FastSaverError(Exception):
    pass

def _headers():
    return {"X-Api-Key": FASTSAVER_API_KEY, "Content-Type": "application/json"}

def _handle_response(response):
    try:
        data = response.json()
    except ValueError:
        raise FastSaverError(f"Invalid JSON (HTTP {response.status_code})")
    
    if not data.get("ok"):
        detail = data.get("detail", "Unknown error")
        if response.status_code == 401:
            raise FastSaverError("مفتاح API غير صالح.")
        elif response.status_code == 429:
            raise FastSaverError("تم تجاوز حد الطلبات. انتظر قليلاً.")
        elif "Insufficient credits" in detail:
            raise FastSaverError("رصيد FastSaver غير كافٍ.")
        else:
            raise FastSaverError(detail)
    return data

def youtube_info(url):
    try:
        r = requests.get(f"{BASE_URL}/youtube/info", params={"url": url}, headers=_headers(), timeout=30)
        return _handle_response(r)
    except requests.RequestException as e:
        raise FastSaverError(f"Network error: {e}")

def youtube_download(video_id, format_type="video", quality=None):
    payload = {"video_id": video_id, "format": format_type}
    if format_type == "video" and quality:
        payload["quality"] = quality
    try:
        r = requests.post(f"{BASE_URL}/youtube/download", json=payload, headers=_headers(), timeout=60)
        return _handle_response(r)
    except requests.RequestException as e:
        raise FastSaverError(f"Network error: {e}")

def fetch_media(url):
    try:
        r = requests.get(f"{BASE_URL}/fetch", params={"url": url}, headers=_headers(), timeout=30)
        return _handle_response(r)
    except requests.RequestException as e:
        raise FastSaverError(f"Network error: {e}")

def get_balance():
    try:
        r = requests.get(f"{BASE_URL}/balance", headers=_headers(), timeout=10)
        return _handle_response(r)
    except requests.RequestException as e:
        raise FastSaverError(f"Network error: {e}")

# --- أوامر البوت ---
YOUTUBE_PATTERN = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! 👋\nأرسل رابط فيديو من المنصات المدعومة وسأقوم بتنزيله لك.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = get_balance()
        credits = data.get("credits", "غير معروف")
        await update.message.reply_text(f"💳 الرصيد: {credits}")
    except FastSaverError as e:
        await update.message.reply_text(f"❌ تعذر جلب الرصيد: {e}")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ الرجاء إرسال رابط صالح.")
        return

    status_msg = await update.message.reply_text("⏳ جاري جلب المعلومات...")

    try:
        if YOUTUBE_PATTERN.search(url):
            data = youtube_info(url)
            video_id = data.get("video_id") or data.get("id") or data.get("videoId")
            if not video_id:
                match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", url)
                if match: video_id = match.group(1)
                else:
                    await status_msg.edit_text("❌ تعذر استخراج معرف الفيديو.")
                    return

            title = data.get("title", "فيديو")
            formats = data.get("formats", [])
            buttons = []
            
            for fmt in formats:
                ftype = fmt.get("type") or fmt.get("format")
                if ftype == "video":
                    quality = fmt.get("quality") or fmt.get("resolution")
                    if quality:
                        size = fmt.get("filesize") or fmt.get("size")
                        label = quality
                        if size:
                            try:
                                size_mb = int(size) / (1024 * 1024)
                                label += f" ({size_mb:.1f} MB)"
                            except: pass
                        buttons.append(InlineKeyboardButton(label, callback_data=f"yt|{video_id}|{quality}"))

            buttons.append(InlineKeyboardButton("🎵 صوت فقط (MP3)", callback_data=f"yt|{video_id}|audio"))

            if not buttons:
                await status_msg.edit_text("❌ لم يتم العثور على جودات متاحة.")
                return

            keyboard = [buttons[i : i + 5] for i in range(0, len(buttons), 5)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text(f"🎬 {title}\n\nاختر الجودة المطلوبة:", reply_markup=reply_markup)

        else:
            data = fetch_media(url)
            download_url = data.get("download_url")
            title = data.get("title") or data.get("description") or "الوسائط"

            if not download_url:
                await status_msg.edit_text("❌ لم يتم العثور على رابط تنزيل مباشر.")
                return

            await status_msg.edit_text("📤 جاري إرسال الوسائط...")
            try:
                await update.message.reply_video(video=download_url, caption=title[:1024])
            except Exception:
                await update.message.reply_text(f"⚠️ تعذر الإرسال المباشر. الرابط:\n{download_url}")
            await status_msg.delete()

    except FastSaverError as e:
        await status_msg.edit_text(f"❌ {e}")
    except Exception as e:
        logger.exception(f"Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ غير متوقع.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")

    if parts[0] != "yt" or len(parts) != 3:
        await query.edit_message_text("⚠️ طلب غير صالح.")
        return

    video_id, quality = parts[1], parts[2]
    await query.edit_message_text("⏳ جاري تنزيل الملف...")

    try:
        if quality == "audio":
            result = youtube_download(video_id, format_type="audio")
        else:
            result = youtube_download(video_id, format_type="video", quality=quality)

        download_url = result.get("download_url")
        filename = result.get("filename", "file")

        if not download_url:
            await query.edit_message_text("❌ لم يتم الحصول على رابط التنزيل.")
            return

        if quality == "audio":
            await query.message.reply_audio(audio=download_url, caption=filename[:1024])
        else:
            await query.message.reply_video(video=download_url, caption=filename[:1024])
        
        await query.message.delete()

    except FastSaverError as e:
        await query.edit_message_text(f"❌ {e}")
    except Exception as e:
        logger.exception(f"Error: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء التنزيل.")

# --- تشغيل البوت ---
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("balance", balance))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
bot_app.add_handler(CallbackQueryHandler(handle_callback))

# --- خادم Flask (لـ Vercel) ---
app = Flask(__name__)

async def _process_update_async(update_data):
    update = Update.de_json(update_data, bot_app.bot)
    await bot_app.process_update(update)

@app.route("/api/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401
    try:
        update_data = request.get_json(force=True)
        if update_data:
            asyncio.run(_process_update_async(update_data))
        return "ok", 200
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return "ok", 200

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "bot": "FastSaver Downloader"}), 200