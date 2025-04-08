import aiohttp
from decouple import config

# Получаем параметры из .env
MOOGOLD_EMAIL = config('MOOGOLD_EMAIL')
MOOGOLD_PASSWORD = config('MOOGOLD_PASSWORD')
MOOGOLD_API_KEY = config('MOOGOLD_API_KEY')
MOOGOLD_SECRET_KEY = config('MOOGOLD_SECRET_KEY')

async def moogold_login():
    url = "https://doc.moogold.com/api/login"  # Гипотетический URL для авторизации
    async with aiohttp.ClientSession() as session:
        data = {
            "email": MOOGOLD_EMAIL,
            "password": MOOGOLD_PASSWORD,
        }
        headers = {
            "API-Key": MOOGOLD_API_KEY,
            "Secret-Key": MOOGOLD_SECRET_KEY
        }
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result["token"]  # Например, возвращаем токен
            else:
                print("Ошибка авторизации", resp.status)
                return None

async def moogold_purchase(token, amount, user_id):
    url = "https://doc.moogold.com/api/purchase"  # Гипотетический URL для покупки
    async with aiohttp.ClientSession() as session:
        data = {
            "amount": amount,
            "userId": user_id,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "API-Key": MOOGOLD_API_KEY,
            "Secret-Key": MOOGOLD_SECRET_KEY
        }
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result
            else:
                print("Ошибка при покупке", resp.status)
                return None
