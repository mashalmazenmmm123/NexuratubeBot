import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from bot import bot_app
from bot.config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)

app = Flask(__name__)

async def _process_update_async(update_data: dict):
    """معالجة تحديث تلجرام بشكل غير متزامن."""
    update = Update.de_json(update_data, bot_app.bot)
    await bot_app.process_update(update)

@app.route("/api/webhook", methods=["POST"])
def webhook():
    """نقطة نهاية Webhook لتلجرام."""
    # التحقق من السر (إذا تم تعيينه)
    if WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret_header != WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret received.")
            return jsonify({"error": "Unauthorized"}), 401

    try:
        update_data = request.get_json(force=True)
        if not update_data:
            return "ok", 200

        # تشغيل المعالجة غير المتزامنة
        asyncio.run(_process_update_async(update_data))
        return "ok", 200

    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        # نعيد 200 لتجنب إعادة المحاولة من تلجرام في حالات الخطأ
        return "ok", 200

@app.route("/", methods=["GET"])
def health():
    """نقطة نهاية للتحقق من الصحة."""
    return jsonify({"status": "running", "bot": "FastSaver Downloader"}), 200 