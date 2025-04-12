import time
import base64
import json
import hmac
import hashlib
import aiohttp
import logging
from decouple import config
from .otp_utils import get_latest_otp_code
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

MOOGOLD_USERNAME = config('MOOGOLD_USERNAME')
MOOGOLD_SECRET_KEY = config('MOOGOLD_SECRET_KEY')

def generate_basic_auth():
    """
    Генерация Basic Auth заголовка.
    """
    basic_auth = base64.b64encode(f"{MOOGOLD_USERNAME}:{MOOGOLD_SECRET_KEY}".encode()).decode()
    auth_header = f"Basic {basic_auth}"
    logger.debug(f"Generated Basic Auth header: {auth_header}")
    return auth_header

def generate_auth_signature(payload: dict, timestamp: str, path: str) -> str:
    """
    Генерация auth подписи согласно документации:
    Формула: hash_hmac('SHA256', <Payload in JSON> + timestamp + path, YOUR_SECRET_KEY)
    """
    try:
        payload_str = json.dumps(payload, separators=(",", ":"))
        string_to_sign = f"{payload_str}{timestamp}{path}"
        signature = hmac.new(
            MOOGOLD_SECRET_KEY.encode(),
            msg=string_to_sign.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        logger.debug(f"Payload string: {string_to_sign}")
        logger.debug(f"Generated auth signature: {signature}")
        return signature
    except Exception as e:
        logger.error(f"Ошибка при генерации подписи: {e}")
        raise

async def moogold_login(path: str, payload: dict):
    """
    Формирование заголовков для авторизации в MooGold API.
    Помимо Basic Auth и timestamp, формируется и auth подпись.
    """
    try:
        timestamp = str(int(time.time()))
        headers = {
            "Authorization": generate_basic_auth(),
            "timestamp": timestamp,
            "Content-Type": "application/json",
            "auth": generate_auth_signature(payload, timestamp, path)
        }
        logger.debug(f"Generated headers for path '{path}': {headers}")
        return headers
    except Exception as e:
        logger.error(f"Ошибка создания заголовков авторизации: {e}")
        return None

async def moogold_create_order(headers, character_id, server_id, product_id, quantity, partner_order_id): 
    if None in [character_id, server_id, product_id, quantity, partner_order_id]:
        error_msg = "Один из параметров для заказа — None. Проверь данные!"
        logger.error(error_msg)
        return {"status": False, "message": error_msg}

    url = "https://moogold.com/wp-json/v1/api/order/create_order"
    data = {
        "path": "order/create_order",
        "data": {
            "category": 1,
            "product-id": str(product_id),
            "quantity": str(quantity),
            "User ID": str(character_id),  
            "Server": str(server_id)         
        },
        "partnerOrderId": partner_order_id
    }
    logger.debug(f"Order creation URL: {url}")
    logger.debug(f"Order payload: {data}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data, headers=headers, allow_redirects=False) as response:
                logger.debug(f"Ответ API: статус {response.status}")
                logger.debug(f"Ответные заголовки: {dict(response.headers)}")
                body = await response.text()
                logger.debug(f"Ответное тело: {body}")

                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    logger.warning(f"Redirect обнаружен, Location: {location}")
                    if "otp_verification.php" in location:
                        logger.info("Перенаправление на OTP-верификацию обнаружено!")
                        otp_code = await get_latest_otp_code()
                        if not otp_code:
                            err = "Не удалось получить OTP код"
                            logger.error(err)
                            return {"status": False, "message": err}
                        confirm_result = await moogold_confirm_otp(headers, otp_code, partner_order_id)
                        return confirm_result
                    else:
                        error_msg = f"Неожиданное перенаправление: {location}"
                        logger.error(error_msg)
                        return {"status": False, "message": error_msg}
                elif response.status == 200:
                    try:
                        json_data = await response.json()
                        logger.debug(f"Декодированный JSON: {json_data}")
                        if not json_data.get("success", True) and "otp" in json_data.get("message", "").lower():
                            logger.info("Ответ от API указывает на необходимость OTP!")
                            otp_code = await get_latest_otp_code()
                            if not otp_code:
                                err = "Не удалось получить OTP код"
                                logger.error(err)
                                return {"status": False, "message": err}
                            confirm_result = await moogold_confirm_otp(headers, otp_code, partner_order_id)
                            return confirm_result
                        return json_data
                    except Exception as decode_error:
                        error_msg = f"Ошибка декодирования JSON: {decode_error}"
                        logger.error(error_msg)
                        return {"status": False, "message": error_msg}
                else:
                    error_msg = f"Ошибка API Moogold: статус {response.status}"
                    logger.error(error_msg)
                    return {"status": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Ошибка запроса к API Moogold: {e}"
            logger.exception(error_msg)
            return {"status": False, "message": error_msg}

async def moogold_confirm_otp(headers, otp_code, partner_order_id):
    """
    Функция подтверждения OTP.
    Отправляем OTP код на страницу верификации.
    """
    url = "https://reseller.moogold.com/otp_verification.php"
    payload = {
        "partnerOrderId": partner_order_id,
        "otp": otp_code
    }
    logger.debug(f"OTP confirmation URL: {url}")
    logger.debug(f"OTP confirmation payload: {payload}")
    try:
        headers = {
            "Authorization": generate_basic_auth(),
            "Content-Type": "application/json"
        }
        logger.debug(f"OTP confirmation headers: {headers}")
    except Exception as e:
        logger.error(f"Ошибка формирования заголовков для подтверждения OTP: {e}")
        return {"status": False, "message": "Ошибка формирования заголовков OTP"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                logger.debug(f"OTP confirmation response статус: {response.status}")
                if response.status == 200:
                    try:
                        confirm_response = await response.json()
                        logger.debug(f"OTP confirmation response JSON: {confirm_response}")
                        return confirm_response
                    except Exception as decode_error:
                        err = f"Ошибка декодирования JSON (OTP): {decode_error}"
                        logger.error(err)
                        return {"status": False, "message": err}
                else:
                    error_msg = f"Ошибка API подтверждения OTP: статус {response.status}"
                    logger.error(error_msg)
                    return {"status": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Ошибка запроса на подтверждение OTP: {e}"
            logger.exception(error_msg)
            return {"status": False, "message": error_msg}
