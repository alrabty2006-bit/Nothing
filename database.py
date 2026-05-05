import os

OWNER_ID = int(os.getenv("OWNER_ID", "5868896814"))
STARS_REQUIRED = 50

users = {}  # user_id -> dict


def get_user(user_id: int, username: str = None) -> dict:
    if user_id not in users:
        users[user_id] = {
            "user_id": user_id,
            "username": username,
            "download_count": 0,
            "has_paid_quality": False,
            "is_subscribed": False,
            "is_exempt": user_id == OWNER_ID,
        }
    if username and not users[user_id].get("username"):
        users[user_id]["username"] = username
    return users[user_id]


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_exempt(user_id: int) -> bool:
    u = users.get(user_id)
    return user_id == OWNER_ID or (u is not None and u.get("is_exempt", False))


def set_exempt(user_id: int, value: bool) -> bool:
    if user_id not in users:
        return False
    users[user_id]["is_exempt"] = value
    return True


def set_subscribed(user_id: int, value: bool):
    get_user(user_id)
    users[user_id]["is_subscribed"] = value


def can_use_high_quality(user_id: int) -> bool:
    if is_owner(user_id) or is_exempt(user_id):
        return True
    u = users.get(user_id)
    return u is not None and u.get("has_paid_quality", False)


def unlock_high_quality(user_id: int):
    get_user(user_id)
    users[user_id]["has_paid_quality"] = True


def increment_download(user_id: int):
    get_user(user_id)
    users[user_id]["download_count"] += 1


def get_all_users() -> list:
    return list(users.values())
