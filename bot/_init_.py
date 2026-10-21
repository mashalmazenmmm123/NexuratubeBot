import logging
from telegram.ext import ApplicationBuilder
from bot.config import BOT_TOKEN
from bot.handlers import setup_handlers

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# بناء تطبيق البوت
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
setup_handlers(bot_app)

logger.info("Bot application initialized successfully.")