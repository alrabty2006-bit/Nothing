import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

OWNER_ID = int(os.getenv("OWNER_ID", "5868896814"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "")


def _owner_url() -> str:
    if OWNER_USERNAME:
        return f"https://t.me/{OWNER_USERNAME.lstrip('@')}"
    return f"tg://user?id={OWNER_ID}"


def main_menu():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("▶️ يوتيوب", callback_data="plt_youtube"),
        InlineKeyboardButton("🎵 تيك توك", callback_data="plt_tiktok"),
        InlineKeyboardButton("📘 فيسبوك", callback_data="plt_facebook"),
    )
    kb.add(
        InlineKeyboardButton("📸 انستغرام", callback_data="plt_instagram"),
        InlineKeyboardButton("🐦 تويتر/X", callback_data="plt_twitter"),
    )
    kb.add(
        InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
        InlineKeyboardButton("📩 تواصل مع المالك", url=_owner_url()),
    )
    return kb


def quality_keyboard(has_hd: bool):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📺 720p HD — مجاني ✅", callback_data="dl_720p"))
    kb.add(InlineKeyboardButton(
        "🎬 1080p Full HD ✅" if has_hd else "🎬 1080p Full HD — 50 نجمة ⭐",
        callback_data="dl_1080p"
    ))
    kb.add(InlineKeyboardButton(
        "✨ 4K Ultra HD ✅" if has_hd else "✨ 4K Ultra HD — 50 نجمة ⭐",
        callback_data="dl_4k"
    ))
    kb.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
    return kb


def subscription_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 قناة ATOM", url="https://t.me/Naru62x"))
    kb.add(InlineKeyboardButton("🤖 بوت HACK", url="https://t.me/Hack696bot"))
    kb.add(InlineKeyboardButton("🎵 تيك توك", url="https://www.tiktok.com/@sou.r31"))
    kb.add(InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub"))
    return kb
