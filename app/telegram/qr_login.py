"""QR-based authorization for the existing Telethon session."""
import asyncio
from getpass import getpass

import qrcode
from telethon.errors import SessionPasswordNeededError

from .client import client

def print_qr(url):
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)

    print("\n" + "=" * 70)
    print("📱 TELEGRAM QR LOGIN")
    print(
        "Telegram → Settings → Devices → "
        "Link Desktop Device orqali QR kodni skaner qiling."
    )
    print("QR kodi:")
    qr.print_ascii(invert=True)
    print("QR URL:", url)
    print("=" * 70 + "\n")

async def login_with_qr():
    await client.connect()

    if await client.is_user_authorized():
        return

    while True:
        qr_login = await client.qr_login()
        print_qr(qr_login.url)

        try:
            await qr_login.wait()
            return

        except asyncio.TimeoutError:
            print("⏳ QR kodi muddati tugadi.")
            print("🔄 Yangi QR kodi yaratilmoqda...")
            continue

        except SessionPasswordNeededError:
            password = getpass("🔐 Telegram 2FA parolini kiriting: ")
            await client.sign_in(password=password)
            return
