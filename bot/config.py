import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FASTSAVER_API_KEY = os.environ.get("FASTSAVER_API_KEY")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "mashalmmm")  # اختياري لكن موصى به
BASE_URL = os.environ.get("BASE_URL", "https://nexuratubebot-qcfmpt8xl-hacker000m7-2371s-projects.vercel.app")  # مثال: https://your-project.vercel.app

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Set it in Vercel Environment Variables.")
if not FASTSAVER_API_KEY:
    raise ValueError("FASTSAVER_API_KEY is missing. Set it in Vercel Environment Variables.")