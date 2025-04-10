import logging
from decimal import Decimal
from asgiref.sync import sync_to_async
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from django.conf import settings
from .models import (
    BotUser, PaymentRequest, Order, Game, CartItem,
    Country, BotSettings, Region, DonationItem
)
from .mogold import moogold_login, moogold_purchase

from django.core.files.base import ContentFile


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
    return ReplyKeyboardMarkup(
        keyboard=[
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
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Сменить регион", callback_data="change_region")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "change_region")
async def cb_change_region(call: CallbackQuery, state: FSMContext):
    countries = await sync_to_async(list)(Country.objects.all())
    keyboard = []
    for i in range(0, len(countries), 2):
        row = [
            InlineKeyboardButton(
                text=c.name,
                callback_data=f"select_country_{c.id}"
            ) for c in countries[i:i+2]
        ]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_profile")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # один вызов — и текст, и новая клавиатура сразу появятся
    await call.message.edit_text(
        "Выберите вашу страну из списка ниже:",
        reply_markup=markup
    )


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
    await wallet_view(call.message)

@router.callback_query(F.data == "info_about_receipt")
async def cb_info_about_receipt(call: CallbackQuery):
    settings_obj = await get_bot_settings()
    await call.message.answer(settings_obj.info_about_receipt, reply_markup=back_to_menu_inline())

@router.message(F.document | F.photo)
async def handle_receipt(message: Message):
    # 1. Получаем или создаём пользователя
    user = await get_or_create_user(message)

    if message.document:
        file_id = message.document.file_id
        filename = message.document.file_name or f"{file_id}.pdf"
    else:
        photo = message.photo[-1]
        file_id = photo.file_id
        filename = f"{file_id}.jpg"

    # 3. Получаем у Telegram путь к файлу и скачиваем его
    tg_file = await message.bot.get_file(file_id)
    file_path = tg_file.file_path  # что‑то вроде "documents/ABC123.pdf"
    file_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file_path}"
    resp = requests.get(file_url)
    resp.raise_for_status()
    content = resp.content

    # 4. Создаём запись в БД (без файла)
    payment = await sync_to_async(PaymentRequest.objects.create)(
        user=user,
        amount=Decimal("0.00"),
        confirmed=False
    )

    # 5. Сохраняем реальный файл в поле receipt_file
    await sync_to_async(payment.receipt_file.save)(
        filename,
        ContentFile(content)
    )

    # 6. Уведомляем пользователя
    await message.answer(
        "✅ Чек получен и сохранён. Статус: в обработке. Ожидайте подтверждения администрацией."
    )
# ======================
# Каталог и выбор игры, региона, доната
# ======================
@router.message(F.text == "🛒 Каталог")
async def catalog_view(message: Message):
    games = await sync_to_async(list)(Game.objects.all())
    inline_rows = [
        [InlineKeyboardButton(text=game.name, callback_data=f"choose_game_{game.id}")]
        for game in games
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)
    await message.answer("Выберите из списка:", reply_markup=markup)

@router.callback_query(F.data.startswith("choose_game_"))
async def cb_choose_game(call: CallbackQuery):
    game_id = call.data.split("_")[-1]
    game = await sync_to_async(Game.objects.get)(id=game_id)
    regions = await sync_to_async(list)(Region.objects.filter(game=game))
    if not regions:
        await call.message.answer("Регионов для этой игры нет.")
        return
    inline_rows = [
        [InlineKeyboardButton(text=f"🌍 {region.name}", callback_data=f"choose_region_{region.id}")]
        for region in regions
    ]
    inline_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)
    
    caption = f"Игра: {game.name}"
    if game.description:
        caption += f"\n\n{game.description}"
    
    if game.image:
        await call.message.delete()
        await call.message.answer_photo(photo=game.image.url, caption=caption, reply_markup=markup)
    else:
        await call.message.edit_text(caption, reply_markup=markup)

@router.callback_query(F.data == "back_to_catalog")
async def cb_back_to_catalog(call: CallbackQuery):
    await catalog_view(call.message)


@router.callback_query(F.data.startswith("choose_region_"))
async def cb_choose_region(call: CallbackQuery):
    await call.answer()

    region_id = int(call.data.split("_")[-1])
    # Загружаем регион (без game, нам нужен только region.name и region.game_id)
    region = await sync_to_async(Region.objects.get)(id=region_id)

    donations = await sync_to_async(
        lambda: list(DonationItem.objects.filter(region=region))
    )()
    if not donations:
        await call.message.edit_text(
            "Для выбранного региона пока нет донат‑предложений.\n"
            "Пожалуйста, выберите другой регион."
        )
        return

    text = f"💰 Доступные валюты для региона «{region.name}»:\n\n"
    for d in donations:
        text += f"• {d.name} — {d.price} С\n"

    inline_rows = [
        [InlineKeyboardButton(
            text=f"{d.name} — {d.price} С",
            callback_data=f"select_donation_{d.id}"
        )]
        for d in donations
    ]
    # Здесь используем region.game_id, а не region.game.id
    inline_rows.append([
        InlineKeyboardButton(
            text="⬅️ Назад к регионам",
            callback_data=f"back_to_regions_{region.game_id}"
        )
    ])
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)

    await call.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith("back_to_regions_"))
async def cb_back_to_regions(call: CallbackQuery):
    await call.answer()

    game_id = int(call.data.split("_")[-1])
    # Загружаем игру и регионы
    game = await sync_to_async(lambda: Region.objects.none())()  # только пример
    # На самом деле вам нужно Game.objects.get, но это вы уже делали
    game = await sync_to_async(Game.objects.get)(id=game_id)
    regions = await sync_to_async(lambda: list(Region.objects.filter(game=game)))()

    inline_rows = [
        [InlineKeyboardButton(
            text=f"🌍 {r.name}",
            callback_data=f"choose_region_{r.id}"
        )]
        for r in regions
    ]
    inline_rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_catalog")
    ])
    text = f"🌍 Выберите регион для игры: {game.name}"
    markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)

    await call.message.edit_text(text, reply_markup=markup)

# ===== Изменения для выбора доната =====

@router.callback_query(F.data.startswith("select_donation_"))
async def cb_select_donation(call: CallbackQuery, state: FSMContext):
    donation_id = call.data.split("_")[-1]
    donation = await sync_to_async(DonationItem.objects.select_related("region__game").get)(id=donation_id)
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    await sync_to_async(CartItem.objects.create)(
         user=user,
         game=donation.region.game,
         quantity=1
    )
    await call.message.answer("Товар успешно добавлен в корзину")


# =========================================

# ======================
# Корзина
# ======================
@router.message(F.text == "🛍 Корзина")
async def cart_view(message: Message):
    user = await get_or_create_user(message)
    # Предзагрузка связанного объекта 'game'
    cart_items = await sync_to_async(list)(
        CartItem.objects.filter(user=user).select_related('game')
    )
    if not cart_items:
        await message.answer("Ваша корзина пуста.", reply_markup=main_menu())
        return
    text = "🛍 Корзина:\n\n" + "\n".join(
        [f"{idx+1}. {item.game.name} x{item.quantity}" for idx, item in enumerate(cart_items)]
    )
    text += "\n\nВыберите действие:"
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")],
            [InlineKeyboardButton(text="📝 Оформить заказ", callback_data="checkout_order")]
        ]
    )
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "remove_last_cart_item")
async def cb_remove_last_cart_item(call: CallbackQuery):
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    last_item = await sync_to_async(CartItem.objects.filter(user=user).last)()
    if last_item:
        await sync_to_async(last_item.delete)()
        await call.message.answer("Удалён последний добавленный товар.")
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
async def cb_checkout_order(call: CallbackQuery):
    await call.message.edit_text("Выберите способ оплаты:")
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 С кошелька", callback_data="pay_with_wallet")],
            [InlineKeyboardButton(text="💳 Стандартный", callback_data="pay_standard")]
        ]
    )
    await call.message.edit_reply_markup(reply_markup=markup)

@router.callback_query(F.data == "pay_standard")
async def cb_pay_standard(call: CallbackQuery, state: FSMContext):
    settings_obj = await get_bot_settings()
    await call.message.edit_text(settings_obj.request_game_id_text)
    await state.set_state(CheckOutState.waiting_for_game_account)

@router.message(CheckOutState.waiting_for_game_account)
async def process_game_account(message: Message, state: FSMContext):
    game_account_info = message.text
    await state.update_data(game_account_info=game_account_info)

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

    user = await get_or_create_user(message)
    cart_items = await sync_to_async(list)(CartItem.objects.filter(user=user))
    for item in cart_items:
        await sync_to_async(Order.objects.create)(
            user=user,
            product_name=item.game.name,
            price=Decimal("355.00"),
            is_paid=False,
            game_account_info=game_account_info
        )

    await sync_to_async(CartItem.objects.filter(user=user).delete)()
    await state.clear()

@router.callback_query(F.data == "pay_with_wallet")
async def cb_pay_with_wallet(call: CallbackQuery):
    user = await sync_to_async(BotUser.objects.get)(telegram_id=call.from_user.id)
    cart_items = await sync_to_async(list)(CartItem.objects.filter(user=user))

    if not cart_items:
        await call.message.answer("Ваша корзина пуста.")
        return

    game = cart_items[0].game  # Получаем первую игру из корзины
    product_id = cart_items[0].game.id  # ID товара, может быть изменено
    quantity = len(cart_items)  # Количество товаров
    character_id = "123456789"  # Character ID, должен быть введен пользователем
    server_id = "3402"  # Сервер, задается статически или вводится пользователем
    partner_order_id = f"ORDER-{user.telegram_id}-{int(time.time())}"  # Уникальный ID заказа

    headers = await moogold_login()
    if not headers:
        await call.message.answer("Ошибка авторизации в Moogold.")
        return

    result = await moogold_create_order(headers, character_id, server_id, product_id, quantity, partner_order_id)

    if result.get("status"):
        await call.message.answer(f"✅ Заказ успешно создан! Номер заказа: {result['account_details']['order_id']}.")
        await sync_to_async(CartItem.objects.filter(user=user).delete)()  # Очищаем корзину
    else:
        await call.message.answer(f"❌ Ошибка при создании заказа: {result['message']}")

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
    text = "Ваши последние заказы:\n\n"
    for order in orders[:5]:
        status = "Оплачен" if order.is_paid else "Не оплачен"
        text += f"#{order.id} | {order.product_name} | {status}\n"
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
# Обработчик кнопки "Меню" (Если понадобится для возврата)
# ======================
@router.message(F.text == "🏠 Меню")
async def back_to_menu_cmd(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu())

@router.message(CheckOutState.waiting_for_game_account)
async def donation_game_account_received(message: Message, state: FSMContext):
    user = await get_or_create_user(message)
    data = await state.get_data()
    game_account = message.text

    donation_id = data["donation_id"]
    donation_name = data["donation_name"]
    game_name = data["game_name"]
    region_name = data["region_name"]
    price = Decimal(str(data["price"]))

    if user.balance < price:
        await message.answer(
            f"Недостаточно средств на кошельке.\n"
            f"Ваш баланс: {user.balance:.2f} С, требуется: {price:.2f} С"
        )
        await state.clear()
        return

    token = await moogold_login()
    if not token:
        await message.answer("❌ Не удалось авторизоваться в Moogold.")
        await state.clear()
        return

    moogold_result = await moogold_purchase(token, amount=float(price), user_id=user.telegram_id)
    if moogold_result.get("success"):
        user.balance -= price
        await sync_to_async(user.save)()

        await sync_to_async(Order.objects.create)(
            user=user,
            product_name=f"{game_name} ({region_name}) — {donation_name}",
            price=price,
            is_paid=True,
            game_account_info=game_account
        )

        await message.answer("✅ Заказ успешно оплачен и оформлен!")
    else:
        await message.answer("❌ Ошибка при оплате через Moogold.")

    await state.clear()
