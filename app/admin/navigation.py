"""Admin navigation workflows."""
from .keyboards import main_menu
from .states import STATES
from .transport import send_message


def start(chat_id):
    STATES.pop(chat_id, None)

    send_message(
        chat_id,
        "🎓 <b>Education Center Admin Bot</b>\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang.",
        main_menu(),
    )
