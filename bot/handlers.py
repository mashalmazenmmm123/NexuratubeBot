import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.fastsaver_client import (
    youtube_info,
    youtube_download,
    fetch_media,
    get_balance,
    FastSaverError,
)

logger = logging.getLogger(__name__)

# نمط للتحقق من روابط يوتيوب
YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start."""
    await update.message.reply_text(
        "مرحباً! 👋\n\n"
        "أرسل رابط فيديو من المنصات المدعومة:\n"
        "• YouTube (فيديو بجودات متعددة أو صوت)\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Facebook\n"
        "• X (Twitter)\n"
        "• Pinterest\n"
        "• RuTube\n"
        "• Likee\n\n"
        "وسأقوم بتنزيله لك."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /balance للتحقق من الرصيد."""
    try:
        data = get_balance()
        credits = data.get("credits", "غير معروف")
        plan = data.get("plan", "غير معروف")
        await update.message.reply_text(
            f"💳 الرصيد: {credits} كريدت\n📦 الخطة: {plan}"
        )
    except FastSaverError as e:
        await update.message.reply_text(f"❌ تعذر جلب الرصيد: {e}")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية التي تحتوي على روابط."""
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("⚠️ الرجاء إرسال رابط صالح يبدأ بـ http أو https.")
        return

    status_msg = await update.message.reply_text("⏳ جاري جلب المعلومات...")

    try:
        if YOUTUBE_PATTERN.search(url):
            # ----- منصة يوتيوب -----
            data = youtube_info(url)

            # استخراج معرف الفيديو (قد يكون بأسماء مختلفة حسب الاستجابة)
            video_id = (
                data.get("video_id")
                or data.get("id")
                or data.get("videoId")
            )
            if not video_id:
                # محاولة استخراجه من الرابط نفسه
                match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", url)
                if match:
                    video_id = match.group(1)
                else:
                    await status_msg.edit_text("❌ تعذر استخراج معرف الفيديو من الرابط.")
                    return

            title = data.get("title", "فيديو")
            formats = data.get("formats", [])

            # بناء أزرار الجودات
            buttons = []
            for fmt in formats:
                # التعامل مع أشكال مختلفة للاستجابة
                ftype = fmt.get("type") or fmt.get("format")
                if ftype == "video":
                    quality = fmt.get("quality") or fmt.get("resolution")
                    if quality:
                        # إضافة حجم الملف إذا توفر
                        size = fmt.get("filesize") or fmt.get("size")
                        label = quality
                        if size:
                            try:
                                size_mb = int(size) / (1024 * 1024)
                                label += f" ({size_mb:.1f} MB)"
                            except (ValueError, TypeError):
                                pass
                        buttons.append(
                            InlineKeyboardButton(
                                label,
                                callback_data=f"yt|{video_id}|{quality}",
                            )
                        )

            # زر الصوت فقط
            buttons.append(
                InlineKeyboardButton(
                    "🎵 صوت فقط (MP3)",
                    callback_data=f"yt|{video_id}|audio",
                )
            )

            if not buttons:
                await status_msg.edit_text("❌ لم يتم العثور على جودات متاحة لهذا الفيديو.")
                return

            # تقسيم الأزرار إلى صفوف (5 كحد أقصى في الصف)
            keyboard = [buttons[i : i + 5] for i in range(0, len(buttons), 5)]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await status_msg.edit_text(
                f"🎬 {title}\n\nاختر الجودة المطلوبة:",
                reply_markup=reply_markup,
            )

        else:
            # ----- المنصات الأخرى عبر /fetch -----
            data = fetch_media(url)
            download_url = data.get("download_url")
            title = data.get("title") or data.get("description") or "الوسائط"

            if not download_url:
                await status_msg.edit_text("❌ لم يتم العثور على رابط تنزيل مباشر.")
                return

            await status_msg.edit_text("📤 جاري إرسال الوسائط...")

            # إرسال الرابط مباشرة إلى تلجرام (تلجرام سيقوم بجلب الملف)
            try:
                await update.message.reply_video(
                    video=download_url,
                    caption=title[:1024],  # الحد الأقصى للتعليق
                )
            except Exception as send_error:
                # في حال فشل الإرسال المباشر (حجم كبير أو صيغة غير مدعومة)
                logger.warning(f"Direct send failed: {send_error}")
                await update.message.reply_text(
                    f"⚠️ تعذر إرسال الملف مباشرة. يمكنك تنزيله من الرابط:\n{download_url}"
                )

            await status_msg.delete()

    except FastSaverError as e:
        logger.error(f"FastSaver error: {e}")
        await status_msg.edit_text(f"❌ {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in handle_url: {e}")
        await status_msg.edit_text("❌ حدث خطأ غير متوقع. حاول مرة أخرى لاحقاً.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على أزرار الجودة."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("|")

    if parts[0] != "yt" or len(parts) != 3:
        await query.edit_message_text("⚠️ طلب غير صالح.")
        return

    video_id = parts[1]
    quality = parts[2]

    await query.edit_message_text("⏳ جاري تنزيل الملف، قد يستغرق بعض الوقت...")

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

        # إرسال الملف إلى المستخدم
        if quality == "audio":
            await query.message.reply_audio(
                audio=download_url,
                caption=filename[:1024],
            )
        else:
            await query.message.reply_video(
                video=download_url,
                caption=filename[:1024],
            )

        await query.message.delete()

    except FastSaverError as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(f"❌ {e}")
    except Exception as e:
        logger.exception(f"Unexpected error in handle_callback: {e}")
        await query.edit_message_text("❌ حدث خطأ غير متوقع أثناء التنزيل. حاول مرة أخرى.")

def setup_handlers(application):
    """تسجيل جميع المعالجات في تطبيق البوت."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)
    )
    application.add_handler(CallbackQueryHandler(handle_callback))