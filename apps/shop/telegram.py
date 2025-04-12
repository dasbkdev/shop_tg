from aiogram import Bot
from django.conf import settings

bot = Bot(token=settings.BOT_TOKEN)

async def send_message(chat_id, text):
    await bot.send_message(chat_id, text)
