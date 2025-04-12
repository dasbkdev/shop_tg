# ====== Обновлённый файл: otp_utils.py ======

import imaplib
import email
import re
import asyncio
from decouple import config

IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = 993
EMAIL_ACCOUNT = config('EMAIL_ACCOUNT')      
EMAIL_PASSWORD = config('EMAIL_PASSWORD')        

async def get_latest_otp_code():
    """
    Асинхронная функция для получения последнего OTP кода из Gmail.
    """
    try:

        return await asyncio.to_thread(fetch_otp_code)
    except Exception as e:
        print(f"Ошибка получения OTP: {e}")
        return None

def fetch_otp_code():
    """
    Синхронная функция для IMAP запроса и извлечения OTP кода.
    """
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    try:
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except Exception as e:
        print(f"Ошибка при логине в IMAP: {e}")
        return None

    try:
        mail.select('inbox')
        
        result, data = mail.search(None, '(UNSEEN SUBJECT "OTP")')
        mail_ids = data[0].split()
        if not mail_ids:
            result, data = mail.search(None, '(SUBJECT "OTP")')
            mail_ids = data[0].split()

        if not mail_ids:
            return None

        latest_email_id = mail_ids[-1]
        result, data = mail.fetch(latest_email_id, '(RFC822)')
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                    except Exception as decode_error:
                        print(f"Ошибка декодирования части письма: {decode_error}")
                        body = ""
                    break
        else:
            charset = msg.get_content_charset() or 'utf-8'
            try:
                body = msg.get_payload(decode=True).decode(charset, errors="replace")
            except Exception as decode_error:
                print(f"Ошибка декодирования письма: {decode_error}")
                body = ""

        otp_match = re.search(r'\b\d{4,8}\b', body)
        if otp_match:
            return otp_match.group()
        return None
    except Exception as e:
        print(f"Ошибка при обработке почты: {e}")
        return None
    finally:
        try:
            mail.close()
        except Exception:
            pass
        mail.logout()
