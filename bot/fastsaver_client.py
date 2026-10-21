import requests
import logging
from bot.config import FASTSAVER_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.fastsaver.io/v1"

class FastSaverError(Exception):
    """خطأ مخصص لاستثناءات FastSaver API."""
    pass

def _headers():
    return {
        "X-Api-Key": FASTSAVER_API_KEY,
        "Content-Type": "application/json",
    }

def _handle_response(response: requests.Response):
    """معالجة موحدة لاستجابات FastSaver."""
    try:
        data = response.json()
    except ValueError:
        raise FastSaverError(f"Invalid JSON response (HTTP {response.status_code})")

    # النجاح الحقيقي هو ok: true، وليس مجرد HTTP 200
    if not data.get("ok"):
        detail = data.get("detail", "Unknown error")
        # معالجة الأخطاء الشائعة برسائل مفهومة
        if response.status_code == 401:
            raise FastSaverError("مفتاح API غير صالح. تحقق من FASTSAVER_API_KEY.")
        elif response.status_code == 429:
            raise FastSaverError("تم تجاوز حد الطلبات. انتظر قليلاً ثم حاول مجدداً.")
        elif "Insufficient credits" in detail:
            raise FastSaverError("رصيد FastSaver غير كافٍ. يرجى شحن الحساب.")
        else:
            raise FastSaverError(detail)
    return data

def youtube_info(url: str) -> dict:
    """جلب معلومات الفيديو والجودات المتاحة (يكلف 2 كريدت)."""
    try:
        response = requests.get(
            f"{BASE_URL}/youtube/info",
            params={"url": url},
            headers=_headers(),
            timeout=30,
        )
        return _handle_response(response)
    except requests.RequestException as e:
        logger.error(f"Network error in youtube_info: {e}")
        raise FastSaverError(f"خطأ في الشبكة أثناء جلب المعلومات: {e}")

def youtube_download(video_id: str, format_type: str = "video", quality: str = None) -> dict:
    """
    تنزيل فيديو يوتيوب أو صوت.
    - format_type: "video" أو "audio"
    - quality: مطلوب فقط عند format_type="video" (مثال: "720p", "1080p")
    """
    payload = {"video_id": video_id, "format": format_type}
    if format_type == "video" and quality:
        payload["quality"] = quality

    try:
        response = requests.post(
            f"{BASE_URL}/youtube/download",
            json=payload,
            headers=_headers(),
            timeout=60,
        )
        return _handle_response(response)
    except requests.RequestException as e:
        logger.error(f"Network error in youtube_download: {e}")
        raise FastSaverError(f"خطأ في الشبكة أثناء التنزيل: {e}")

def fetch_media(url: str) -> dict:
    """جلب وسائط من المنصات الأخرى (تيك توك، إنستغرام، فيسبوك، إلخ)."""
    try:
        response = requests.get(
            f"{BASE_URL}/fetch",
            params={"url": url},
            headers=_headers(),
            timeout=30,
        )
        return _handle_response(response)
    except requests.RequestException as e:
        logger.error(f"Network error in fetch_media: {e}")
        raise FastSaverError(f"خطأ في الشبكة أثناء جلب الوسائط: {e}")

def get_balance() -> dict:
    """التحقق من رصيد الكريدت (مجاني)."""
    try:
        response = requests.get(
            f"{BASE_URL}/balance",
            headers=_headers(),
            timeout=10,
        )
        return _handle_response(response)
    except requests.RequestException as e:
        raise FastSaverError(f"خطأ في الشبكة أثناء جلب الرصيد: {e}")