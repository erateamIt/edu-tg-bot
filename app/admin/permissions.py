"""Admin Bot user access policy."""
from app.core.config import ADMIN_USER_ID

def is_admin(user_id):
    # ADMIN_USER_ID 0 bo'lsa vaqtincha barcha foydalanuvchilarga ruxsat beradi.
    # Production'da albatta o'z Telegram ID'ingizni yozing.
    return ADMIN_USER_ID == 0 or user_id == ADMIN_USER_ID
