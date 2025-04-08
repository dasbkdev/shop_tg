import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from asgiref.sync import sync_to_async

from django.conf import settings

from .models import (
    BotUser, PaymentRequest, Order, Game, CartItem,
    Country, BotSettings
)

router = Router()
logging.basicConfig(level=logging.DEBUG)

# ======================
# Состояния FSM
# ======================

class ChangeRegionState(StatesGroup):
    waiting_for_region = State()

class TopUpState(StatesGroup):
    waiting_for_amount = State()

class CheckOutState(StatesGroup):
    waiting_for_game_account = State()


# ======================
# Клавиатуры
# ======================

def main_menu():
    # Главное меню без "Настройки"
    # Кнопки: Профиль, Кошелёк, Каталог, Корзина, История, Поддержка
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Меню")],
            [KeyboardButton(text="🧑‍💼 Профиль"), KeyboardButton(text="💼 Кошелёк")],
            [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="🛍 Корзина")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="📞 Поддержка")],
        ],
        resize_keyboard=True
    )


def back_to_menu_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Вернуться", callback_data="go_back_to_menu")]
        ]
    )


# ======================
# Хелперы
# ======================

async def get_or_create_user(message: Message):
    user, _ = await sync_to_async(BotUser.objects.get_or_create)(
        telegram_id=message.from_user.id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
        }
    )
    return user


async def get_bot_settings():
    # Берём единственную запись BotSettings (или создаём, если нет)
    settings_obj, _ = await sync_to_async(BotSettings.objects.get_or_create)(id=1)
    return settings_obj


# ======================
# /start
# ======================

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user = await get_or_create_user(message)
    await message.answer(
        "Добро пожаловать в магазин! Выберите действие:",
        reply_markup=main_menu()
    )


# ======================
# Профиль
# ======================

@router.message(F.text == "🧑‍💼 Профиль")
async def profile_view(message: Message):
    user = await get_or_create_user(message)
    text = (
        "🧑‍💼 Профиль:\n\n"
        f"👤 Никнейм: {user.username or 'не указан'}\n"
        f"🌍 Регион: {user.region or 'не указан'}\n"
        f"📅 Дата регистрации: {user.registration_date.strftime('%d.%m.%Y')}\n"
    )
    # Инлайн-кнопки: Сменить регион, Назад
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Сменить регион", callback_data="change_region")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "change_region")
async def cb_change_region(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Выберите вашу страну из списка ниже:")
    # Выгружаем список стран из БД
    countries = await sync_to_async(list)(Country.objects.all())
    inline_rows = []
    for country in countries:
        inline_rows.append([
            InlineKeyboardButton(text=country.name, callback_data=f"select_country_{country.id}")
        ])
    inline_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile")])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)
    await call.message.edit_reply_markup(markup)


@router.callback_query(F.data.startswith("select_country_"))
async def cb_select_country(call: CallbackQuery):
    country_id = call.data.split("_")[-1]
    try:
        country_obj = await sync_to_async(Country.objects.get)(id=country_id)
    except Country.DoesNotExist:
        await call.message.answer("Страна не найдена.")
        return
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    user.region = country_obj.name
    await sync_to_async(user.save)()
    await call.message.edit_text(
        f"Регион успешно изменён на: {country_obj.name}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile")]
            ]
        )
    )


@router.callback_query(F.data == "back_to_profile")
async def cb_back_to_profile(call: CallbackQuery):
    # Просто повторно вызываем profile_view
    await profile_view(call.message)


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("Главное меню:", reply_markup=main_menu())


# ======================
# Кошелёк
# ======================

@router.message(F.text == "💼 Кошелёк")
async def wallet_view(message: Message):
    user = await get_or_create_user(message)
    text = (
        "🇰🇬 Ваш кошелёк (KGS)\n\n"
        f"Текущий баланс: {user.balance:.2f} С\n\n"
        "Выберите действие:"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
            [InlineKeyboardButton(text="➕ Пополнить", callback_data="top_up")]
        ]
    )
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "top_up")
async def cb_top_up(call: CallbackQuery):
    # Берём реквизиты для пополнения из BotSettings
    settings_obj = await get_bot_settings()
    text = (
        "💳 Реквизиты для оплаты:\n\n"
        f"{settings_obj.wallet_requisites}\n\n"
        "После оплаты отправьте чек или PDF‑файл в этот же чат."
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_wallet")],
            [InlineKeyboardButton(text="Инфо!", callback_data="info_about_receipt")]
        ]
    )
    await call.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == "back_to_wallet")
async def cb_back_to_wallet(call: CallbackQuery):
    # Эмулируем сообщение "💼 Кошелёк"
    await wallet_view(call.message)


@router.callback_query(F.data == "info_about_receipt")
async def cb_info_about_receipt(call: CallbackQuery):
    settings_obj = await get_bot_settings()
    await call.message.answer(settings_obj.info_about_receipt, reply_markup=back_to_menu_inline())


# === Обработка отправки чека (фото/pdf) ===
@router.message(F.document | F.photo)
async def handle_receipt(message: Message):
    # Проверим, находится ли пользователь в процессе пополнения или оплаты
    # Но для упрощения — примем любой файл как чек
    user = await get_or_create_user(message)
    file_id = message.document.file_id if message.document else message.photo[-1].file_id

    # Создаём PaymentRequest
    await sync_to_async(PaymentRequest.objects.create)(
        user=user,
        amount=Decimal("0.00"),  # Можно ввести логику суммы, если нужно
        receipt_file=file_id,
        confirmed=False
    )
    await message.answer("✅ Чек получен. Статус: в обработке. Ожидайте подтверждения администрацией.")


# ======================
# Каталог
# ======================

@router.message(F.text == "🛒 Каталог")
async def catalog_view(message: Message):
    await message.answer("Выберите из списка:")
    # Выводим игры из админки
    games = await sync_to_async(list)(Game.objects.all())
    inline_rows = []
    for game in games:
        inline_rows.append([
            InlineKeyboardButton(text=game.name, callback_data=f"choose_game_{game.id}")
        ])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)
    await message.answer("Список игр:", reply_markup=markup)


@router.callback_query(F.data.startswith("choose_game_"))
async def cb_choose_game(call: CallbackQuery):
    game_id = call.data.split("_")[-1]
    try:
        game = await sync_to_async(Game.objects.get)(id=game_id)
    except Game.DoesNotExist:
        await call.message.answer("Игра не найдена.")
        return

    text = f"**{game.name}**\n\n{game.description or ''}"
    # Картинку можно отправить отдельно, если есть
    if game.image:
        # Предполагаем, что это FileField. Нужно писать отдельную логику, как получить URL
        # Для упрощения отправим только текст
        pass

    # Пример кнопок — меняются из админки, но сейчас жёстко зашиваем
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить в корзину", callback_data=f"add_to_cart_{game.id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")]
        ]
    )
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)


@router.callback_query(F.data == "back_to_catalog")
async def cb_back_to_catalog(call: CallbackQuery):
    await catalog_view(call.message)


@router.callback_query(F.data.startswith("add_to_cart_"))
async def cb_add_to_cart(call: CallbackQuery):
    game_id = call.data.split("_")[-1]
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    try:
        game = await sync_to_async(Game.objects.get)(id=game_id)
    except Game.DoesNotExist:
        await call.message.answer("Игра не найдена.")
        return

    # Добавляем в корзину
    await sync_to_async(CartItem.objects.create)(user=user, game=game)
    await call.message.answer(f"Товар '{game.name}' добавлен в корзину.")


# ======================
# Корзина
# ======================

@router.message(F.text == "🛍 Корзина")
async def cart_view(message: Message):
    user = await get_or_create_user(message)
    cart_items = await sync_to_async(list)(CartItem.objects.filter(user=user))

    if not cart_items:
        await message.answer("Ваша корзина пуста.", reply_markup=main_menu())
        return

    # Формируем список товаров
    text = "🛍 Корзина:\n\n"
    for idx, item in enumerate(cart_items, start=1):
        text += f"{idx}. {item.game.name} x{item.quantity}\n"
    text += "\nВыберите действие:"

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ Удалить последний", callback_data="remove_last_cart_item"),
                InlineKeyboardButton(text="🗑 Удалить всё", callback_data="clear_cart")
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"),
                InlineKeyboardButton(text="📝 Оформить заказ", callback_data="checkout_order")
            ]
        ]
    )
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "remove_last_cart_item")
async def cb_remove_last_cart_item(call: CallbackQuery):
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    last_item = await sync_to_async(CartItem.objects.filter(user=user).last)()
    if last_item:
        await sync_to_async(last_item.delete)()
        await call.message.answer(f"Удалён последний добавленный товар.")
    await cart_view(call.message)


@router.callback_query(F.data == "clear_cart")
async def cb_clear_cart(call: CallbackQuery):
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    await sync_to_async(CartItem.objects.filter(user=user).delete)()
    await call.message.answer("Корзина очищена.")
    await cart_view(call.message)


# ======================
# Оформление заказа
# ======================

@router.callback_query(F.data == "checkout_order")
async def cb_checkout_order(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Выберите способ оплаты:")
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Оплатить с кошелька", callback_data="pay_with_wallet")],
            [InlineKeyboardButton(text="💳 Оплатить стандартным способом", callback_data="pay_standard")],
            [InlineKeyboardButton(text="⬅️ Вернуться", callback_data="back_to_main")]
        ]
    )
    await call.message.edit_reply_markup(markup)


@router.callback_query(F.data == "pay_standard")
async def cb_pay_standard(call: CallbackQuery, state: FSMContext):
    # Берём текст запроса игрового ID из админки
    settings_obj = await get_bot_settings()
    await call.message.edit_text(settings_obj.request_game_id_text)
    await state.set_state(CheckOutState.waiting_for_game_account)


@router.message(CheckOutState.waiting_for_game_account)
async def process_game_account(message: Message, state: FSMContext):
    game_account_info = message.text
    # Сохраняем во временный storage
    await state.update_data(game_account_info=game_account_info)

    # Теперь отправляем реквизиты для оплаты
    settings_obj = await get_bot_settings()
    text = (
        "💳 Реквизиты для оплаты:\n\n"
        f"{settings_obj.payment_requisites}\n\n"
        "После оплаты отправьте чек или PDF‑файл в этот же чат."
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Вернуться", callback_data="back_to_main")],
            [InlineKeyboardButton(text="Инфо!", callback_data="info_about_receipt")]
        ]
    )
    await message.answer(text, reply_markup=markup)

    # Создаём заказ(ы) из корзины
    user = await get_or_create_user(message)
    cart_items = await sync_to_async(list)(CartItem.objects.filter(user=user))
    for item in cart_items:
        await sync_to_async(Order.objects.create)(
            user=user,
            product_name=item.game.name,
            price=Decimal("355.00"),  # заглушка, можно считать по-другому
            is_paid=False,
            game_account_info=game_account_info
        )
    # Чистим корзину
    await sync_to_async(CartItem.objects.filter(user=user).delete)()

    await state.clear()


@router.callback_query(F.data == "pay_with_wallet")
async def cb_pay_with_wallet(call: CallbackQuery):
    # Логика списания с кошелька (пока не реализована)
    await call.message.answer("Оплата с кошелька временно не доступна.")
    await cb_back_to_main(call)


# ======================
# История заказов
# ======================

@router.message(F.text == "📜 История")
async def history_view(message: Message):
    user = await get_or_create_user(message)
    orders = await sync_to_async(list)(Order.objects.filter(user=user).order_by('-created_at'))
    if not orders:
        await message.answer("На странице 1 у вас пока нет записей в истории.", reply_markup=main_menu())
        return

    # Выводим последние 5 заказов (пример)
    text = "Ваши последние заказы:\n\n"
    for order in orders[:5]:
        text += f"#{order.id} | {order.product_name} | {'Оплачен' if order.is_paid else 'Не оплачен'}\n"
    await message.answer(text, reply_markup=main_menu())


# ======================
# Поддержка
# ======================

@router.message(F.text == "📞 Поддержка")
async def support_view(message: Message):
    settings_obj = await get_bot_settings()
    text = "📞 Контакты администратора"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Связаться", url=settings_obj.admin_contact)]
        ]
    )
    await message.answer(text, reply_markup=markup)


# ======================
# Кнопка "Меню"
# ======================

@router.message(F.text == "🏠 Меню")
async def back_to_menu_cmd(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu())
