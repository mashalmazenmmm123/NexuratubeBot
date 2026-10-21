# NexuraTube

بوت تيليجرام لتنزيل فيديوهات يوتيوب بجودات 360p–1080p مع حد أقصى 50 ميجابايت.

## المتطلبات

1. **حساب Vercel** (خطة Hobby أو Pro).
2. **مستودع GitHub** (عام أو خاص).
3. **بوت تيليجرام** (توكن من @BotFather).
4. **قاعدة بيانات Redis** (Upstash أو Vercel KV) لتخزين الجلسات مؤقتًا.
5. **GitHub Token** (صلاحية `actions:write` على المستودع).

## خطوات النشر

### 1. إعداد مستودع GitHub
- ارفع الملفات إلى المستودع.
- أضف السر `TELEGRAM_BOT_TOKEN` في **Settings → Secrets and variables → Actions**.

### 2. إعداد Vercel
- اربط المستودع بـ Vercel.
- أضف متغيرات البيئة التالية في **Settings → Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: توكن البوت.
  - `TELEGRAM_WEBHOOK_SECRET`: نص سري عشوائي (مثال: `mysecret123`).
  - `GITHUB_TOKEN`: توكن GitHub (صلاحية `actions:write`).
  - `GITHUB_REPO`: `username/repo` (مثال: `myuser/nexuratube`).
  - `GITHUB_WORKFLOW_ID`: `download.yml` (اسم ملف الـ workflow).
  - `REDIS_URL`: رابط Upstash Redis (يبدأ بـ `rediss://`).
  - `YOUTUBE_PO_TOKEN`: قيمة PO Token من YouTube (إن توفرت).
  - `YOUTUBE_VISITOR_DATA`: قيمة `visitor_data` من YouTube (إن توفرت).
  - `YOUTUBE_PLAYER_CLIENTS`: قائمة العملاء، مثال: `web,android,ios`.
  - `YOUTUBE_COOKIES_FILE`: مسار ملف كوكيز YouTube بصيغة Netscape (اختياري).
  - `YOUTUBE_COOKIES_FROM_BROWSER`: اسم المتصفح إذا أردت استيراد الكوكيز مباشرة من المتصفح، مثال: `chrome` أو `firefox`.
  - `YOUTUBE_USER_AGENT`: User-Agent اختياري لتمثيل المتصفح.
  - `YOUTUBE_ACCEPT_LANGUAGE`: قيمة Accept-Language مثل `en-US,en;q=0.9`.

> ملاحظة مهمة: إذا ظهر الخطأ `Sign in to confirm you’re not a bot` في YouTube، فالأصل هو أنك تحتاج إلى تمرير `PO Token` و`visitor_data` أو ملف cookies. هذا المشروع الآن يدعم تلك المتغيرات تلقائيًا داخل yt-dlp.

### 3. تعيين Webhook
بعد نشر Vercel، نفّذ:
```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://<your-vercel-app>.vercel.app/api/webhook",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
  }'
