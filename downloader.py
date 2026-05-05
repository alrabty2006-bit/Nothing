"""
downloader.py — unified yt-dlp wrapper for ATOM bot.

Strategy per platform:
  • YouTube / Vimeo  → separate streams allowed; merge with ffmpeg + faststart
  • Instagram        → single pre-merged mp4 only; no merge attempts
  • Facebook         → single pre-merged mp4 only; no merge attempts
  • TikTok           → single pre-merged mp4 only; no merge attempts
  • Twitter / X      → single pre-merged mp4 only; no merge attempts

The +faststart post-processor flag moves the moov atom to the front of the
file so Telegram can stream it without stuttering or cutting.
"""

import glob
import os
import subprocess
import tempfile

TMP_DIR = tempfile.gettempdir()

# Desktop UA — most reliable across all platforms
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Platforms that serve pre-merged single-stream files
_SINGLE_STREAM_HOSTS = (
    "instagram.com", "instagr.am",
    "facebook.com", "fb.watch", "fb.com",
    "tiktok.com", "vm.tiktok.com",
    "twitter.com", "x.com", "t.co",
)


def _is_single_stream(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in _SINGLE_STREAM_HOSTS)


def _quality_format(quality: str) -> str:
    """Format string for platforms that support separate streams (YouTube etc.)."""
    if quality == "720p":
        return (
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo[height<=720]+bestaudio"
            "/best[height<=720][ext=mp4]"
            "/best[height<=720]"
            "/best"
        )
    if quality == "1080p":
        return (
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo[height<=1080]+bestaudio"
            "/best[height<=1080][ext=mp4]"
            "/best[height<=1080]"
            "/best"
        )
    if quality == "4k":
        return (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio"
            "/best[ext=mp4]"
            "/best"
        )
    return "best"


def _build_base(output_template: str) -> list:
    """Common yt-dlp flags shared by all attempts."""
    return [
        "yt-dlp",
        "--no-playlist",
        "--no-warnings",
        "--no-check-certificates",
        "--socket-timeout", "60",
        "--retries", "10",
        "--fragment-retries", "10",
        "--concurrent-fragments", "4",
        "--merge-output-format", "mp4",
        # ★ THE FIX FOR STUTTERING: move moov atom to start of file
        "--postprocessor-args", "ffmpeg:-movflags +faststart",
        "--user-agent", USER_AGENT,
        "--add-header", "Accept-Language:en-US,en;q=0.9",
        "--add-header", "Accept:*/*",
        "-o", output_template,
    ]


def download_video(url: str, quality: str, user_id: int) -> str:
    """Download a video and return the local file path."""

    # Remove leftover files from previous attempts
    for f in glob.glob(os.path.join(TMP_DIR, f"atom_{user_id}_*")):
        try:
            os.remove(f)
        except OSError:
            pass

    output_tpl = os.path.join(TMP_DIR, f"atom_{user_id}_%(id)s.%(ext)s")
    base = _build_base(output_tpl)
    single = _is_single_stream(url)

    if single:
        # These platforms only expose a single pre-merged stream.
        # Never try bestvideo+bestaudio — it will always fail.
        attempts = [
            base + ["-f", "best[ext=mp4]/bestvideo[ext=mp4]/best", url],
            base + ["-f", "best", url],
            base + [url],
        ]
    else:
        # YouTube and similar — quality-aware with graceful fallback
        attempts = [
            base + ["-f", _quality_format(quality), url],
            base + ["-f", "best[ext=mp4]/best", url],
            base + [url],
        ]

    last_error = ""
    for args in attempts:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=360,
            )
            if result.returncode == 0:
                path = _find_file(user_id)
                # If ffmpeg produced a temp/part file, wait for final mp4
                if path.endswith(".part") or path.endswith(".ytdl"):
                    raise Exception("اكتمل التحميل لكن الملف غير مكتمل، حاول مجدداً")
                return path
            last_error = result.stderr + result.stdout
        except subprocess.TimeoutExpired:
            raise Exception(
                "⏱ انتهت مهلة التحميل\n"
                "الفيديو كبير جداً أو الاتصال بطيء، حاول مع فيديو أقصر"
            )
        except Exception as e:
            if "غير مكتمل" in str(e):
                raise
            last_error = str(e)

    _raise_friendly(last_error, single, url)


def _raise_friendly(stderr: str, is_single: bool, url: str) -> None:
    """Convert raw yt-dlp error into a user-friendly Arabic message."""
    e = stderr.lower()

    if "private" in e or "login required" in e or "sign in" in e or "authenticate" in e:
        raise Exception(
            "🔒 الفيديو خاص أو يتطلب تسجيل دخول\n"
            "تأكد أن الحساب/المنشور عام ثم أعد المحاولة"
        )
    if "copyright" in e or "dmca" in e:
        raise Exception("⚠️ الفيديو محمي بحقوق الملكية ولا يمكن تحميله")
    if "not available" in e or "removed" in e or "deleted" in e or "no longer available" in e:
        raise Exception("❌ الفيديو غير متاح أو تم حذفه")
    if "unsupported url" in e or "no video formats" in e or "cannot parse" in e:
        raise Exception("❌ الرابط غير مدعوم — تأكد أنه رابط فيديو صحيح")
    if "too short" in e or "http error 404" in e:
        raise Exception("❌ الرابط غير صحيح أو الفيديو محذوف")
    if "geo" in e or "not available in your country" in e:
        raise Exception("🌍 الفيديو محظور في منطقتك")
    if "http error 429" in e or "rate limit" in e:
        raise Exception("⏳ تم إيقاف التحميل مؤقتاً من المنصة، انتظر دقيقة وأعد المحاولة")

    if "instagram" in url.lower() or "instagr.am" in url.lower():
        raise Exception(
            "❌ فشل تحميل فيديو انستغرام\n\n"
            "الأسباب المحتملة:\n"
            "• الحساب خاص — تأكد أنه عام\n"
            "• الرابط منشور/ريل فقط (Post أو Reel)\n"
            "• Stories لا يمكن تحميلها بدون تسجيل دخول"
        )
    if "facebook.com" in url.lower() or "fb.watch" in url.lower():
        raise Exception(
            "❌ فشل تحميل فيديو فيسبوك\n\n"
            "الأسباب المحتملة:\n"
            "• المنشور خاص أو للأصدقاء فقط\n"
            "• جرّب فتح الرابط في متصفح خاص أولاً"
        )

    raise Exception(
        "❌ فشل التحميل\n\n"
        "تأكد من:\n"
        "• أن الرابط صحيح ويفتح عندك\n"
        "• أن الفيديو/الحساب عام\n"
        "• ثم أعد المحاولة"
    )


def _find_file(user_id: int) -> str:
    candidates = [
        f for f in glob.glob(os.path.join(TMP_DIR, f"atom_{user_id}_*"))
        if not f.endswith(".part") and not f.endswith(".ytdl")
    ]
    if not candidates:
        # Accept part files as last resort
        candidates = glob.glob(os.path.join(TMP_DIR, f"atom_{user_id}_*"))
    if not candidates:
        raise Exception("❌ لم يتم إيجاد الملف بعد التحميل")
    return max(candidates, key=os.path.getmtime)


def cleanup(filepath: str) -> None:
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass


def is_url(text: str) -> bool:
    t = text.strip()
    return t.startswith("http://") or t.startswith("https://")


def is_paid_quality(quality: str) -> bool:
    return quality in ("1080p", "4k")


def file_size_mb(filepath: str) -> float:
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except OSError:
        return 0.0
