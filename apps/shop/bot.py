import asyncio
import django
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apps.shop.handlers import router
import logging
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Текущая директория:", os.getcwd())

logging.basicConfig(level=logging.DEBUG)

django.setup()

from django.conf import settings

bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())


dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())