import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from config import BOT_TOKEN, ADMIN_GROUP_ID
from database import db
from states import RegistrationStates, BroadcastStates, BanStates
from keyboards import get_admin_menu, get_broadcast_confirmation, get_broadcast_start

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    try:
        # Проверяем, является ли пользователь участником группы админов
        member = await bot.get_chat_member(ADMIN_GROUP_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Ошибка проверки админа: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    user_id = message.from_user.id
    
    # Проверяем, заблокирован ли пользователь
    if await db.is_user_banned(user_id):
        await message.answer("❌ Вы заблокированы и не можете использовать этого бота.")
        return
    
    # Проверяем, является ли пользователь админом
    if await is_admin(user_id):
        await message.answer(
            "👋 Добро пожаловать, администратор!\n\n"
            "Выберите действие:",
            reply_markup=get_admin_menu()
        )
    else:
        # Проверяем, зарегистрирован ли пользователь
        user_data = await db.get_user(user_id)
        if user_data:
            await message.answer(
                "👋 Добро пожаловать!\n\n"
                "Вы уже зарегистрированы в системе."
            )
        else:
            await message.answer(
                "👋 Добро пожаловать!\n\n"
                "Для использования бота необходимо пройти регистрацию.\n"
                "Пожалуйста, введите ваше полное имя (ФИО):"
            )
            await state.set_state(RegistrationStates.waiting_for_name)

# Обработчики регистрации
@dp.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода ФИО"""
    await state.update_data(full_name=message.text)
    await message.answer("Отлично! Теперь введите ваш город:")
    await state.set_state(RegistrationStates.waiting_for_city)

@dp.message(RegistrationStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    """Обработка ввода города"""
    await state.update_data(city=message.text)
    await message.answer("Теперь введите адрес вашего магазина или магазинов:")
    await state.set_state(RegistrationStates.waiting_for_address)

@dp.message(RegistrationStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    """Обработка ввода адреса и завершение регистрации"""
    user_data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or "Без username"
    
    # Сохраняем пользователя в БД
    await db.add_user(
        user_id=user_id,
        username=username,
        full_name=user_data['full_name'],
        city=user_data['city'],
        shop_address=message.text
    )
    
    # Отправляем уведомление в группу админов
    admin_message = (
        "🆕 Новая регистрация!\n\n"
        f"👤 ФИО: {user_data['full_name']}\n"
        f"🌍 Город: {user_data['city']}\n"
        f"🏪 Адрес магазина: {message.text}\n"
        f"📱 Username: @{username}\n"
        f"🆔 ID: {user_id}"
    )
    
    try:
        await bot.send_message(ADMIN_GROUP_ID, admin_message)
    except Exception as e:
        logger.error(f"Ошибка отправки в группу админов: {e}")
    
    await message.answer(
        "✅ Регистрация завершена!\n\n"
        "Ваши данные переданы администраторам. "
        "Теперь вы будете получать рассылки от бота."
    )
    await state.clear()

# Обработчики для админов
@dp.callback_query(F.data == "broadcast")
async def handle_broadcast_button(callback: CallbackQuery):
    """Обработка нажатия кнопки рассылки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора!")
        return
    
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\n"
        "Вы хотите сделать рассылку всем зарегистрированным пользователям?",
        reply_markup=get_broadcast_start()
    )

@dp.callback_query(F.data == "start_broadcast")
async def handle_start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало процесса рассылки"""
    await callback.message.edit_text(
        "📝 Введите сообщение для рассылки:"
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@dp.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    await state.update_data(
        broadcast_message_id=message.message_id,
        broadcast_chat_id=message.chat.id
    )
    
    # Получаем количество пользователей
    users = await db.get_all_users()
    user_count = len(users)
    
    await message.answer(
        f"📢 Сообщение для рассылки готово!\n\n"
        f"👥 Количество получателей: {user_count}\n\n"
        f"Начать рассылку?",
        reply_markup=get_broadcast_confirmation()
    )
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@dp.callback_query(F.data == "confirm_broadcast")
async def handle_confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и запуск рассылки"""
    data = await state.get_data()
    broadcast_message_id = data.get('broadcast_message_id')
    broadcast_chat_id = data.get('broadcast_chat_id')
    
    if not broadcast_message_id or not broadcast_chat_id:
        await callback.answer("❌ Ошибка: сообщение не найдено!")
        return
    
    await callback.message.edit_text("🚀 Рассылка запущена! Отправляю сообщения...")
    
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    success_count = 0
    failed_count = 0
    
    # Отправляем сообщения
    for user in users:
        try:
            await bot.copy_message(
                chat_id=user['user_id'],
                from_chat_id=broadcast_chat_id,
                message_id=broadcast_message_id
            )
            success_count += 1
            
            # Отправляем отчет админу
            report_message = f"✅ {user['full_name']} (@{user['username']}) - Получено"
            await callback.message.answer(report_message)
            
            # Небольшая задержка чтобы не нарушить лимиты
            await asyncio.sleep(0.1)
            
        except TelegramBadRequest as e:
            failed_count += 1
            error_message = f"❌ {user['full_name']} (@{user['username']}) - Ошибка: {str(e)}"
            await callback.message.answer(error_message)
        except Exception as e:
            failed_count += 1
            error_message = f"❌ {user['full_name']} (@{user['username']}) - Неизвестная ошибка"
            await callback.message.answer(error_message)
    
    # Итоговый отчет
    final_report = (
        f"📊 Рассылка завершена!\n\n"
        f"✅ Успешно доставлено: {success_count}\n"
        f"❌ Ошибок: {failed_count}\n"
        f"👥 Всего пользователей: {len(users)}"
    )
    await callback.message.answer(final_report)
    
    # Отправляем меню администратора
    await callback.message.answer(
        "🎛 Панель администратора\n\nВыберите действие:",
        reply_markup=get_admin_menu()
    )
    await state.clear()

@dp.callback_query(F.data == "ban_user")
async def handle_ban_user_button(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки блокировки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора!")
        return
    
    await callback.message.edit_text(
        "🚫 Блокировка пользователя\n\n"
        "Введите username пользователя (с @ или без):"
    )
    await state.set_state(BanStates.waiting_for_username)

@dp.message(BanStates.waiting_for_username)
async def process_ban_username(message: Message, state: FSMContext):
    """Обработка username для блокировки"""
    username = message.text.strip()
    
    # Блокируем пользователя
    success = await db.ban_user_by_username(username)
    
    if success:
        await message.answer(f"✅ Пользователь @{username.replace('@', '')} заблокирован!")
    else:
        await message.answer(f"❌ Пользователь @{username.replace('@', '')} не найден или уже заблокирован!")
        
    # Отправляем меню администратора
    await message.answer(
        "🎛 Панель администратора\n\nВыберите действие:",
        reply_markup=get_admin_menu()
    )
    
    await state.clear()

@dp.callback_query(F.data == "cancel_broadcast")
async def handle_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена.\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu()
    )

# Обработчик для неизвестных сообщений
@dp.message()
async def handle_unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    if await is_admin(message.from_user.id):
        await message.answer(
            "Используйте команду /start для доступа к меню администратора.",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            "Используйте команду /start для начала работы с ботом."
        )

async def main():
    """Основная функция запуска бота"""
    # Инициализируем базу данных
    await db.init_db()
    
    # Запускаем бота
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 