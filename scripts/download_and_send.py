import os
import sys
import requests
import yt_dlp

from api.yt_utils import build_yt_dlp_options

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
MESSAGE_ID = os.environ.get("MESSAGE_ID")
URL = os.environ["URL"]
FORMAT_ID = os.environ.get("FORMAT_ID") or "best[ext=mp4]/best"
MAX_SIZE = 50 * 1024 * 1024  # 50 MB

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": CHAT_ID, "text": text})

def edit_message(message_id, text):
    requests.post(f"{TELEGRAM_API}/editMessageText", json={
        "chat_id": CHAT_ID, "message_id": message_id, "text": text
    })

def main():
    if MESSAGE_ID:
        edit_message(MESSAGE_ID, "⏳ جاري تجهيز الفيديو...\n\nقد يستغرق بعض الوقت حسب الحجم والموقع.")

    ydl_opts = {
        "format": FORMAT_ID,
        "outtmpl": "video.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
    }
    ydl_opts.update(build_yt_dlp_options())

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(URL, download=True)
            filename = ydl.prepare_filename(info)
            if not filename:
                raise ValueError("لم يتم إرجاع اسم ملف صالح من المحرك.")
    except Exception as e:
        send_message(f"❌ فشل التنزيل: {str(e)}")
        if MESSAGE_ID:
            edit_message(MESSAGE_ID, f"❌ فشل التنزيل:\n{str(e)}")
        sys.exit(1)

    if not os.path.exists(filename):
        for candidate in [
            "video.mp4",
            "video.webm",
            "video.mkv",
            "video.mov",
            "video.%(ext)s",
        ]:
            if candidate == "video.%(ext)s":
                continue
            if os.path.exists(candidate):
                filename = candidate
                break

    # التحقق من الحجم
    filesize = os.path.getsize(filename)
    if filesize > MAX_SIZE:
        send_message(
            f"⚠️ حجم الفيديو ({filesize / (1024*1024):.1f} MB) "
            f"يتجاوز الحد المسموح 50 MB."
        )
        sys.exit(0)

    # إرسال الفيديو إلى تيليجرام
    try:
        with open(filename, "rb") as f:
            files = {"video": f}
            data = {"chat_id": CHAT_ID, "caption": info.get("title", "")}
            resp = requests.post(f"{TELEGRAM_API}/sendVideo", data=data, files=files, timeout=60)
            if resp.status_code != 200:
                send_message(f"❌ فشل إرسال الفيديو: {resp.text}")
                if MESSAGE_ID:
                    edit_message(MESSAGE_ID, f"❌ فشل إرسال الفيديو:\n{resp.text}")
            else:
                if MESSAGE_ID:
                    edit_message(MESSAGE_ID, "✅ تم إرسال الفيديو بنجاح.")
    except Exception as e:
        send_message(f"❌ خطأ أثناء الإرسال: {str(e)}")
        if MESSAGE_ID:
            edit_message(MESSAGE_ID, f"❌ خطأ أثناء الإرسال:\n{str(e)}")

if __name__ == "__main__":
    main()
