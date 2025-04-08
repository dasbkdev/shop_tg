from django.contrib import admin
from .models import (
    BotUser, PaymentRequest, Order,
    Game, CartItem, Country, BotSettings,
    Region, DonationItem
)

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'region', 'balance', 'registration_date')
    search_fields = ('telegram_id', 'username', 'region')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'confirmed', 'created_at')
    list_filter = ('confirmed', 'status')
    search_fields = ('user__telegram_id', 'user__username')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product_name', 'price', 'is_paid', 'created_at')
    list_filter = ('is_paid',)
    search_fields = ('user__telegram_id', 'user__username', 'product_name')

class RegionInline(admin.StackedInline):
    model = Region
    extra = 1

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [RegionInline]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'quantity', 'added_at')
    search_fields = ('user__username', 'game__name')


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment_requisites', 'admin_contact')
    fieldsets = (
        ("Реквизиты для оплаты заказа", {
            'fields': ('payment_requisites',)
        }),
        ("Информация об отправке чека", {
            'fields': ('info_about_receipt',)
        }),
        ("Контакты администратора", {
            'fields': ('admin_contact',)
        }),
        ("Реквизиты для пополнения кошелька", {
            'fields': ('wallet_requisites',)
        }),
        ("Текст запроса игрового ID", {
            'fields': ('request_game_id_text',)
        }),
    )

class DonationItemInline(admin.TabularInline):
    model = DonationItem
    extra = 1

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    inlines = [DonationItemInline]
