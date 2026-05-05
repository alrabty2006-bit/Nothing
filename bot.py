import os
import logging
from dotenv import load_dotenv
import telebot
from telebot.types import Message, CallbackQuery, PreCheckoutQuery

from database import (
    get_user, is_owner, is_exempt, set_exempt, set_subscribed,
    can_use_high_quality, unlock_high_quality, increment_download,
    get_all_users, OWNER_ID, STARS_REQUIRED,
)
from downloader import download_video, cleanup, is_url, is_paid_quality, file_size_mb
from ai_helper import ask_ai
from keyboards import main_menu, quality_keyboard, subscription_keyboard
from messages import (
    WELCOME, SUBSCRIPTION_REQUIRED, HD_UNLOCKED,
    PLATFORM_SELECTED, SELECT_QUALITY, DOWNLOADING,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set!")

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

REQUIRED_CHANNELS = ["Naru62x", "Hack696bot"]

# user_id -> {"state": str, "platform": str}
user_states: dict[int, dict] = {}
# user_id -> url waiting to be downloaded
pending_urls: dict[int, str] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def check_membership(user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(f"@{ch}", user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True


def ensure_subscribed(message_or_chat_id, user_id: int) -> bool:
    if is_owner(user_id) or is_exempt(user_id):
        return True
    if check_membership(user_id):
        set_subscribed(user_id, True)
        return True
    chat_id = (
        message_or_chat_id.chat.id
        if hasattr(message_or_chat_id, "chat")
        else message_or_chat_id
    )
    bot.send_message(chat_id, SUBSCRIPTION_REQUIRED, reply_markup=subscription_keyboard())
    return False


def send_quality_menu(chat_id: int, user_id: int, url: str):
    pending_urls[user_id] = url
    has_hd = can_use_high_quality(user_id)
    bot.send_message(chat_id, SELECT_QUALITY, reply_markup=quality_keyboard(has_hd))


def do_download(chat_id: int, user_id: int, quality: str):
    url = pending_urls.get(user_id)
    if not url:
        bot.send_message(chat_id, "❌ لم أجد الرابط، أرسله مجدداً.")
        return

    msg = bot.send_message(chat_id, DOWNLOADING)
    filepath = None
    try:
        filepath = download_video(url, quality, user_id)
        increment_download(user_id)
        pending_urls.pop(user_id, None)

        labels = {"720p": "720p HD", "1080p": "1080p Full HD", "4k": "4K Ultra HD"}
        caption = f"✅ *تم التحميل بجودة {labels.get(quality, quality)}* 🎬\n📥 @Hack696bot"

        size_mb = file_size_mb(filepath)

        # Show upload indicator
        try:
            bot.send_chat_action(chat_id, "upload_video")
        except Exception:
            pass

        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass

        if size_mb > 49:
            # File too large for Telegram bot API (50 MB limit)
            bot.send_message(
                chat_id,
                f"⚠️ الفيديو كبير جداً ({size_mb:.1f} MB)\n"
                "تيليغرام يسمح بـ 50 MB كحد أقصى\n"
                "جرّب جودة أقل مثل 720p",
                reply_markup=main_menu(),
            )
        else:
            with open(filepath, "rb") as f:
                bot.send_video(
                    chat_id,
                    f,
                    caption=caption,
                    supports_streaming=True,
                    timeout=120,
                    reply_markup=main_menu(),
                )

    except Exception as e:
        log.error(f"Download error for user {user_id}: {e}")
        try:
            bot.edit_message_text(str(e), chat_id, msg.message_id, reply_markup=main_menu())
        except Exception:
            bot.send_message(chat_id, str(e), reply_markup=main_menu())
    finally:
        if filepath:
            cleanup(filepath)


# ── Commands ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(msg: Message):
    uid = msg.from_user.id
    get_user(uid, msg.from_user.username)
    if not ensure_subscribed(msg, uid):
        return
    bot.send_message(msg.chat.id, WELCOME, reply_markup=main_menu())


@bot.message_handler(commands=["help"])
def cmd_help(msg: Message):
    bot.send_message(
        msg.chat.id,
        "📖 *تعليمات بوت ATOM*\n\n"
        "• أرسل أي رابط فيديو مباشرة\n"
        "• أو اختر منصة من الأزرار\n"
        "• 720p مجاني ✅\n"
        "• 1080p و4K تحتاج 50 نجمة ⭐\n\n"
        "*الأوامر:*\n`/start` `/stats` `/help`",
    )


@bot.message_handler(commands=["stats"])
def cmd_stats(msg: Message):
    uid = msg.from_user.id
    u = get_user(uid, msg.from_user.username)
    hd = "✅ مفعّل" if can_use_high_quality(uid) else "🔒 مقفل (50 نجمة)"
    exempt = "نعم" if (is_owner(uid) or is_exempt(uid)) else "لا"
    bot.send_message(
        msg.chat.id,
        f"📊 *إحصائياتك*\n\n"
        f"👤 المعرف: `{uid}`\n"
        f"📥 التحميلات: {u['download_count']}\n"
        f"🎬 جودة HD: {hd}\n"
        f"🎁 معفى: {exempt}",
    )


@bot.message_handler(commands=["exempt"])
def cmd_exempt(msg: Message):
    if not is_owner(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ للمالك فقط")
        return
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(msg.chat.id, "الاستخدام: `/exempt 123456789`")
        return
    tid = int(parts[1])
    get_user(tid)
    set_exempt(tid, True)
    unlock_high_quality(tid)
    bot.send_message(msg.chat.id, f"✅ تم إعفاء المستخدم `{tid}` وفُتحت له جميع الجودات")


@bot.message_handler(commands=["unexempt"])
def cmd_unexempt(msg: Message):
    if not is_owner(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ للمالك فقط")
        return
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(msg.chat.id, "الاستخدام: `/unexempt 123456789`")
        return
    tid = int(parts[1])
    set_exempt(tid, False)
    bot.send_message(msg.chat.id, f"✅ تم إلغاء إعفاء `{tid}`")


@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(msg: Message):
    if not is_owner(msg.from_user.id):
        return
    text = msg.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.send_message(msg.chat.id, "الاستخدام: `/broadcast رسالتك هنا`")
        return
    sent = 0
    for u in get_all_users():
        try:
            bot.send_message(u["user_id"], f"📢 *رسالة من المالك:*\n\n{text}")
            sent += 1
        except Exception:
            pass
    bot.send_message(msg.chat.id, f"✅ أُرسلت لـ {sent} مستخدم")


@bot.message_handler(commands=["users"])
def cmd_users(msg: Message):
    if not is_owner(msg.from_user.id):
        return
    bot.send_message(msg.chat.id, f"👥 *إجمالي المستخدمين: {len(get_all_users())}*")


# ── Text messages ─────────────────────────────────────────────────────────────

@bot.message_handler(content_types=["text"])
def handle_text(msg: Message):
    uid = msg.from_user.id
    text = msg.text.strip()
    chat_id = msg.chat.id

    get_user(uid, msg.from_user.username)
    if not ensure_subscribed(msg, uid):
        return

    state = user_states.get(uid, {})

    # Waiting for AI question
    if state.get("state") == "waiting_ai":
        user_states.pop(uid, None)
        thinking = bot.send_message(chat_id, "🤖 جارٍ التفكير...")
        answer = ask_ai(text)
        bot.delete_message(chat_id, thinking.message_id)
        bot.send_message(chat_id, f"🤖 *إجابة ATOM AI:*\n\n{answer}", reply_markup=main_menu())
        return

    # URL received
    if is_url(text):
        user_states.pop(uid, None)
        send_quality_menu(chat_id, uid, text)
        return

    # Waiting for URL but received non-URL
    if state.get("state") == "waiting_url":
        bot.send_message(chat_id, "❌ أرسل رابطاً يبدأ بـ https://")
        return

    # Default: AI answer
    thinking = bot.send_message(chat_id, "🤖 جارٍ التفكير...")
    answer = ask_ai(text)
    bot.delete_message(chat_id, thinking.message_id)
    bot.send_message(chat_id, f"🤖 {answer}", reply_markup=main_menu())


# ── Callback queries ──────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call: CallbackQuery):
    uid = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data

    bot.answer_callback_query(call.id)
    get_user(uid, call.from_user.username)
    if not ensure_subscribed(chat_id, uid):
        return

    # Check subscription
    if data == "check_sub":
        if check_membership(uid):
            set_subscribed(uid, True)
            bot.send_message(chat_id, WELCOME, reply_markup=main_menu())
        else:
            bot.send_message(
                chat_id,
                "❌ لم أتحقق من اشتراكك. اشترك في جميع القنوات ثم اضغط *تحققت*.",
                reply_markup=subscription_keyboard(),
            )
        return

    if data == "back_main":
        user_states.pop(uid, None)
        bot.send_message(chat_id, "🏠 القائمة الرئيسية:", reply_markup=main_menu())
        return

    if data == "my_stats":
        u = get_user(uid)
        hd = "✅ مفعّل" if can_use_high_quality(uid) else "🔒 مقفل (50 نجمة)"
        bot.send_message(
            chat_id,
            f"📊 *إحصائياتك*\n\n📥 التحميلات: {u['download_count']}\n🎬 جودة HD: {hd}",
            reply_markup=main_menu(),
        )
        return

    # Platform selection
    platforms = {
        "plt_youtube": "YouTube",
        "plt_tiktok": "TikTok",
        "plt_facebook": "Facebook",
        "plt_instagram": "Instagram",
        "plt_twitter": "Twitter/X",
    }
    if data in platforms:
        user_states[uid] = {"state": "waiting_url", "platform": platforms[data]}
        bot.send_message(chat_id, PLATFORM_SELECTED.format(platform=platforms[data]))
        return

    # Quality selection
    if data.startswith("dl_"):
        quality = data.replace("dl_", "")
        if is_paid_quality(quality) and not can_use_high_quality(uid):
            prices = [telebot.types.LabeledPrice("50 نجمة ⭐", STARS_REQUIRED)]
            bot.send_invoice(
                chat_id,
                title="🔓 فتح الجودة العالية",
                description="ادفع 50 نجمة لتفعيل 1080p و4K بشكل دائم",
                invoice_payload=f"hd_unlock_{uid}",
                provider_token="",
                currency="XTR",
                prices=prices,
            )
            return
        do_download(chat_id, uid, quality)
        return


# ── Stars payment ─────────────────────────────────────────────────────────────

@bot.pre_checkout_query_handler(func=lambda q: True)
def handle_pre_checkout(query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def handle_payment(msg: Message):
    uid = msg.from_user.id
    stars = msg.successful_payment.total_amount
    if stars >= STARS_REQUIRED:
        unlock_high_quality(uid)
        bot.send_message(
            msg.chat.id,
            f"⭐ *شكراً على دعمك!* تم استلام {stars} نجمة\n\n{HD_UNLOCKED}",
            reply_markup=main_menu(),
        )


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("ATOM Bot is starting...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
