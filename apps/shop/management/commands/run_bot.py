from django.core.management.base import BaseCommand
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
from django.conf import settings

from apps.shop.handlers import router

logging.basicConfig(level=logging.DEBUG)

class Command(BaseCommand):
    help = "Запускает Telegram-бота"

    def handle(self, *args, **options):
        self.stdout.write("Запуск бота...")
        asyncio.run(self.run_bot())

    async def run_bot(self):
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode='HTML')
        )
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)
        await dp.start_polling(bot)
