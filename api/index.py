import os
import json
import uuid
import requests
from flask import Flask, request, jsonify
import yt_dlp
import redis

from api.yt_utils import build_yt_dlp_options

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")          # مثال: "username/repo"
GITHUB_WORKFLOW_ID = os.environ.get("GITHUB_WORKFLOW_ID")  # مثال: "download.yml"
REDIS_URL = os.environ.get("REDIS_URL")              # رابط Upstash Redis

r = redis.from_url(REDIS_URL) if REDIS_URL else None

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- دوال مساعدة ----------
def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API}/editMessageText", json=payload)

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API}/sendPhoto", json=payload)

def send_chat_action(chat_id, action="typing"):
    requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": action})

def extract_info(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
    }
    ydl_opts.update(build_yt_dlp_options())
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def get_qualities(info):
    """إرجاع قاموس {height: format_dict} للجودات المطلوبة (360, 480, 720, 1080)"""
    target_heights = [360, 480, 720, 1080]
    formats = info.get("formats", [])
    available = {}
    for f in formats:
        height = f.get("height")
        if height in target_heights and f.get("vcodec") != "none":
            # تفضيل صيغة mp4 إن وجدت
            if height not in available or f.get("ext") == "mp4":
                available[height] = f
    return available

# ---------- Webhook ----------
@app.route("/api/webhook", methods=["POST"])
def webhook():
    # التحقق من السر
    if WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != WEBHOOK_SECRET:
            return jsonify({"ok": False}), 403

    update = request.get_json()
    if not update:
        return jsonify({"ok": True})

    # معالجة الضغط على زر
    if "callback_query" in update:
        return handle_callback(update["callback_query"])

    # معالجة الرسائل النصية
    message = update.get("message")
    if not message or "text" not in message:
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    if not text.startswith("http"):
        send_message(chat_id, "الرجاء إرسال رابط فيديو صالح.")
        return jsonify({"ok": True})

    # إرسال حالة انتظار
    send_chat_action(chat_id, "typing")
    wait_resp = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": "🔍 جاري تحليل الرابط..."}
    ).json()
    wait_msg_id = wait_resp["result"]["message_id"]

    try:
        info = extract_info(text)
    except Exception as e:
        edit_message(chat_id, wait_msg_id, f"❌ حدث خطأ أثناء التحليل: {str(e)}")
        return jsonify({"ok": True})

    title = info.get("title", "بدون عنوان")
    duration = info.get("duration", 0)
    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "غير متاح"
    thumbnail = info.get("thumbnail")

    qualities = get_qualities(info)
    if not qualities:
        edit_message(chat_id, wait_msg_id, "❌ لم يتم العثور على جودات متاحة (360p–1080p).")
        return jsonify({"ok": True})

    # إنشاء جلسة وتخزينها في Redis (صالح لمدة ساعة)
    session_id = str(uuid.uuid4())
    if r:
        r.setex(f"session:{session_id}", 3600, json.dumps({"url": text, "chat_id": chat_id}))

    # بناء أزرار الجودات
    keyboard = []
    for height in sorted(qualities.keys()):
        f = qualities[height]
        filesize = f.get("filesize") or f.get("filesize_approx")
        if filesize:
            size_mb = filesize / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
            if filesize > 50 * 1024 * 1024:
                size_str += " ⚠️ (يتجاوز 50MB)"
        else:
            size_str = "حجم غير معروف"
        label = f"{height}p ({size_str})"
        callback_data = f"q:{session_id}:{f['format_id']}"
        keyboard.append([{"text": label, "callback_data": callback_data}])

    reply_markup = {"inline_keyboard": keyboard}
    caption = f"🎬 *{title}*\n⏱ المدة: {duration_str}\n\nاختر الجودة (الحد الأقصى 50 ميجابايت):"

    # حذف رسالة الانتظار وإرسال الصورة مع المعلومات
    requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": wait_msg_id})
    if thumbnail:
        send_photo(chat_id, thumbnail, caption, reply_markup)
    else:
        send_message(chat_id, caption, reply_markup, parse_mode="Markdown")

    return jsonify({"ok": True})

# ---------- معالجة اختيار الجودة ----------
def handle_callback(callback):
    callback_id = callback["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback.get("data", "")

    if not data.startswith("q:"):
        return jsonify({"ok": True})

    _, session_id, format_id = data.split(":", 2)

    session_data = None
    if r:
        raw = r.get(f"session:{session_id}")
        if raw:
            session_data = json.loads(raw)

    if not session_data:
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": "انتهت صلاحية الجلسة. أعد إرسال الرابط.",
            "show_alert": True
        })
        return jsonify({"ok": True})

    url = session_data["url"]

    # الرد على الاستعلام
    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
        "callback_query_id": callback_id,
        "text": "⏳ جاري بدء التنزيل..."
    })

    # تعديل الرسالة الأصلية لإزالة الأزرار وإظهار حالة الانتظار
    edit_message(chat_id, message_id, "⏳ جاري تنزيل الفيديو... (قد يستغرق بعض الوقت)")

    # إطلاق GitHub Actions
    if GITHUB_TOKEN and GITHUB_REPO and GITHUB_WORKFLOW_ID:
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        payload = {
            "ref": "main",  # عدّله إذا كان الفرع الافتراضي مختلفًا
            "inputs": {
                "url": url,
                "format_id": format_id,
                "chat_id": str(chat_id),
                "message_id": str(message_id)
            }
        }
        resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_ID}/dispatches",
            headers=headers,
            json=payload
        )
        if resp.status_code not in (204, 201):
            edit_message(chat_id, message_id, f"❌ فشل بدء التنزيل: {resp.text}")
    else:
        edit_message(chat_id, message_id, "❌ إعدادات GitHub Actions غير مكتملة.")

    return jsonify({"ok": True})
