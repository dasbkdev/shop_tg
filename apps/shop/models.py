from django.db import models
from django.utils import timezone

# === Пользователь бота ===
class BotUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)

    # Дополнительные поля
    region = models.CharField(max_length=255, blank=True, null=True)  # Регион
    registration_date = models.DateTimeField(default=timezone.now)    # Дата регистрации
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.username or self.telegram_id} | {self.region or 'Регион не указан'}"


# === Запрос на оплату (пополнение) ===
class PaymentRequest(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_file = models.FileField(upload_to='receipts/', blank=True, null=True)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Статус для удобства
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Payment #{self.id} | User: {self.user}"


# === Заказ ===
class Order(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Можно добавить поле для хранения игрового ID
    game_account_info = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} | {self.product_name} | {self.user}"


# === Модель для списка игр в каталоге ===
class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='games/', blank=True, null=True)  # Картинка для игры
    # Можно хранить дополнительную инфу, если нужно

    def __str__(self):
        return self.name

# === Модель для корзины (товары, которые пользователь выбрал) ===
class CartItem(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='cart_items')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CartItem | {self.user} | {self.game} (x{self.quantity})"


# === Модель для списка стран (смена региона) ===
class Country(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# === Модель для хранения текстов, реквизитов и прочих настроек бота ===
class BotSettings(models.Model):
    # Реквизиты для стандартной оплаты
    payment_requisites = models.TextField(
        default="•  💰 Сумма заказа: 355 С\n•  🏦 Мбанк: +996557336612\n•  👤 Получатель: Расим К."
    )
    # Информация об отправке чека
    info_about_receipt = models.TextField(
        default=(
            "Информация об отправке чека:\n\n"
            "• Чек должен быть четким...\n"
            "• При отправке файла в формате PDF...\n\n"
            "Принимаемые через бот банки...\n"
        )
    )
    # Контакты администратора
    admin_contact = models.CharField(
        max_length=255,
        default="https://t.me/dasbkdev",
        help_text="Ссылка на профиль владельца"
    )
    wallet_requisites = models.TextField(
        default="•  💰 Сумма пополнения: 500.00 С\n•  🏦 Мбанк: +996557336612\n•  👤 Получатель: Расим К."
    )
    request_game_id_text = models.TextField(
        default="Пожалуйста, укажите ваш игровой ID и сервер ID.\nНапример: 487283643 (2451)"
    )

    def __str__(self):
        return "Настройки Бота (редактируйте меня для изменения текстов/реквизитов)"  


class Region(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='regions')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    region_image = models.ImageField(upload_to='regions/', blank=True, null=True)

    def __str__(self):
        return f"{self.game.name} | {self.name}"

class DonationItem(models.Model):
    """Предмет доната, привязанный к конкретному региону."""
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='donations')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    extra_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.region.name})"