import time
import hashlib
import base64
import aiohttp
from decouple import config

# Получаем параметры из .env
MOOGOLD_USERNAME = config('MOOGOLD_USERNAME')  # Партнер ID
MOOGOLD_SECRET_KEY = config('MOOGOLD_SECRET_KEY')  # Секретный ключ

async def moogold_login():
    """
    Функция для создания заголовков авторизации Moogold API.
    """
    try:
        timestamp = str(int(time.time()))
        basic_auth = base64.b64encode(f"{MOOGOLD_USERNAME}:{MOOGOLD_SECRET_KEY}".encode()).decode()

        headers = {
            "Authorization": f"Basic {basic_auth}",
            "timestamp": timestamp,
            "Content-Type": "application/json"
        }
        return headers
    except Exception as e:
        print(f"Ошибка создания заголовков авторизации: {e}")
        return None

async def moogold_create_order(headers, character_id, server_id, product_id, quantity, partner_order_id):
    """
    Функция для создания заказа через Moogold API.
    """
    url = "https://reseller.moogold.com/wp-json/v1/api/order/create_order"

    data = {
        "path": "order/create_order",
        "data": {
            "category": "1",
            "product-id": product_id,
            "quantity": str(quantity),
            "User ID": str(character_id),
            "Server": str(server_id)
        },
        "partnerOrderId": partner_order_id
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": False, "message": f"Ошибка API Moogold: {response.status}"}
        except Exception as e:
            return {"status": False, "message": f"Ошибка запроса к API Moogold: {e}"}

async def moogold_purchase(token, amount, user_id):
    url = "https://doc.moogold.com/api/purchase"
    async with aiohttp.ClientSession() as session:
        data = {
            "amount": amount,
            "userId": user_id
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