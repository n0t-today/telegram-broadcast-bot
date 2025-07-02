from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu():
    """Клавиатура для админов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
            [InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data="ban_user")]
        ]
    )
    return keyboard

def get_broadcast_confirmation():
    """Клавиатура подтверждения рассылки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, начать рассылку", callback_data="confirm_broadcast")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_broadcast")]
        ]
    )
    return keyboard

def get_broadcast_start():
    """Клавиатура согласия на рассылку"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, хочу сделать рассылку", callback_data="start_broadcast")],
            [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="cancel_broadcast")]
        ]
    )
    return keyboard 