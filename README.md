# 🤖 بوت ATOM — لتحميل الفيديوهات

بوت تيليغرام احترافي لتحميل الفيديوهات من يوتيوب، تيك توك، فيسبوك، انستغرام وتويتر.

---

## 📁 هيكل المشروع

```
atom-bot-python/
├── bot.py            ← الملف الرئيسي
├── database.py       ← إدارة المستخدمين
├── downloader.py     ← تحميل الفيديوهات
├── ai_helper.py      ← الذكاء الاصطناعي
├── keyboards.py      ← أزرار التيليغرام
├── messages.py       ← رسائل البوت
├── requirements.txt  ← المكتبات
├── Procfile          ← لـ Railway
└── .env.example      ← مثال على المتغيرات
```

---

## 🚀 طريقة الرفع على GitHub ثم Railway

### الخطوة 1 — رفع المشروع على GitHub

```bash
git init
git add .
git commit -m "ATOM Bot initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/atom-bot.git
git push -u origin main
```

### الخطوة 2 — الاستضافة على Railway

1. اذهب إلى [railway.app](https://railway.app) وسجّل دخول
2. اضغط **New Project** ثم **Deploy from GitHub repo**
3. اختر المستودع الذي رفعت فيه الكود
4. اضغط على **Variables** وأضف المتغيرات التالية:

| اسم المتغير | القيمة |
|---|---|
| `TELEGRAM_BOT_TOKEN` | التوكن من @BotFather |
| `GEMINI_API_KEY` | مفتاح Gemini AI |
| `OWNER_ID` | معرفك في تيليغرام |

5. تأكد أن Railway يقرأ **Procfile** — سيشغّل تلقائياً:
   ```
   worker: python bot.py
   ```
6. اضغط **Deploy** ✅

---

## ⚙️ المتطلبات

ملف `requirements.txt` يحتوي على:

```
pyTelegramBotAPI==4.20.0   ← مكتبة تيليغرام
yt-dlp==2024.12.13         ← تحميل الفيديوهات
google-generativeai==0.8.3 ← الذكاء الاصطناعي Gemini
python-dotenv==1.0.1       ← قراءة ملف .env
requests==2.32.3           ← طلبات HTTP
```

---

## 🔧 تشغيل محلي (للتطوير)

```bash
# 1. نسخ ملف المتغيرات
cp .env.example .env
# ثم عدّل .env وضع التوكن والمفاتيح

# 2. تثبيت المكتبات
pip install -r requirements.txt

# 3. تشغيل البوت
python bot.py
```

---

## 🎯 مميزات البوت

- ✅ اشتراك إجباري في القنوات قبل الاستخدام
- 📺 جودة 720p مجانية للجميع
- 🎬 جودة 1080p و4K مقابل 50 نجمة ⭐ (دائمة)
- 🤖 ذكاء اصطناعي Gemini يجيب على كل شيء
- 👑 المالك معفى تلقائياً من كل القيود
- `/exempt [ID]` — إعفاء مستخدم
- `/broadcast [رسالة]` — إرسال لجميع المستخدمين

---

## 📌 ملاحظات مهمة

- على Railway اختر نوع الخدمة **Worker** وليس **Web Service**
- yt-dlp مثبت تلقائياً كمكتبة Python، لا حاجة لتثبيته يدوياً
- إذا أردت تحميل فيديوهات فيسبوك الخاصة، تحتاج ملف cookies
