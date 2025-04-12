from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    BotUser, PaymentRequest, Order,
    Game, CartItem, Country, BotSettings,
    Region, DonationItem
)

admin.site.site_header = _("Галактическая Админ-панель")
admin.site.site_title = _("Галактическое Администрирование")
admin.site.index_title = _("Добро пожаловать во вселенную управления")

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'region', 'balance', 'registration_date')
    search_fields = ('telegram_id', 'username', 'region')
    fieldsets = (
        (_("Основная информация"), {
            'fields': ('telegram_id', 'username', 'first_name', 'region')
        }),
        (_("Баланс и дата регистрации"), {
            'fields': ('balance', 'registration_date'),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Пользователь бота")
    verbose_name_plural = _("Пользователи бота")

@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'confirmed', 'created_at')
    list_filter = ('confirmed', 'status')
    search_fields = ('user__telegram_id', 'user__username')
    readonly_fields = ('receipt_preview',)
    fieldsets = (
        (_("Основные данные"), {
            'fields': ('user', 'amount', 'receipt_file', 'status', 'confirmed', 'receipt_preview')
        }),
        (_("Временная метка"), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Запрос на оплату")
    verbose_name_plural = _("Запросы на оплату")

    def receipt_preview(self, obj):
        if obj.receipt_file:
            url = obj.receipt_file.url
            name = obj.receipt_file.name.split('/')[-1]
            return format_html(
                '<a href="{0}" target="_blank">{1}</a><br>'
                '<iframe src="{0}" width="600" height="400"></iframe>',
                url, name
            )
        return "—"
    receipt_preview.short_description = "Чек (PDF)"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product_name', 'price', 'is_paid', 'created_at')
    list_filter = ('is_paid',)
    search_fields = ('user__telegram_id', 'user__username', 'product_name')
    fieldsets = (
        (_("Информация о заказе"), {
            'fields': ('user', 'product_name', 'game_account_info')
        }),
        (_("Оплата"), {
            'fields': ('price', 'is_paid'),
        }),
        (_("Временная метка"), {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Заказ")
    verbose_name_plural = _("Заказы")

class DonationItemInline(admin.TabularInline):
    model = DonationItem
    extra = 1
    verbose_name = _("Предмет доната")
    verbose_name_plural = _("Предметы доната")

class RegionInline(admin.StackedInline):
    model = Region
    extra = 1
    verbose_name = _("Регион")
    verbose_name_plural = _("Регионы")

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [RegionInline]
    fieldsets = (
        (_("Основная информация"), {
            'fields': ('name', 'description')
        }),
        (_("Медиа"), {
            'fields': ('image',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Игра")
    verbose_name_plural = _("Игры")

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'quantity', 'added_at')
    search_fields = ('user__username', 'game__name')
    fieldsets = (
        (_("Основная информация"), {
            'fields': ('user', 'game', 'quantity')
        }),
        (_("Временная метка"), {
            'fields': ('added_at',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Элемент корзины")
    verbose_name_plural = _("Корзина")

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    verbose_name = _("Страна")
    verbose_name_plural = _("Страны")

@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment_requisites', 'admin_contact')
    fieldsets = (
        (_("Реквизиты для оплаты заказа"), {
            'fields': ('payment_requisites',)
        }),
        (_("Информация об отправке чека"), {
            'fields': ('info_about_receipt',)
        }),
        (_("Контакты администратора"), {
            'fields': ('admin_contact',)
        }),
        (_("Реквизиты для пополнения кошелька"), {
            'fields': ('wallet_requisites',)
        }),
        (_("Текст запроса игрового ID"), {
            'fields': ('request_game_id_text',)
        }),
    )
    verbose_name = _("Настройка бота")
    verbose_name_plural = _("Настройки бота")

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    search_fields = ('name', 'game__name')
    inlines = [DonationItemInline]
    fieldsets = (
        (_("Основные данные"), {
            'fields': ('game', 'name', 'description')
        }),
        (_("Изображение региона"), {
            'fields': ('region_image',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Регион")
    verbose_name_plural = _("Регионы")

@admin.register(DonationItem)
class DonationItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'site_price', 'bot_price')
    search_fields = ('name', 'region__name')
    fieldsets = (
        (_("Основные данные"), {
            'fields': ('region', 'name', 'site_price', 'bot_price')
        }),
        (_("Дополнительно"), {
            'fields': ('extra_info',),
            'classes': ('collapse',),
        }),
    )
    verbose_name = _("Предмет доната")
    verbose_name_plural = _("Предметы доната")
