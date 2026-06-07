import logging
from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
from core.database import db
from handlers.client_bot import client_router
from handlers.client_admin import client_admin_router
from core.config import WEBHOOK_HOST, WEBHOOK_PORT

# Master Dispatcher အား တစ်ခုတည်းသာ တည်ဆောက်မည်
client_dp = Dispatcher()
client_dp.include_router(client_router)
client_dp.include_router(client_admin_router)

async def start_client_bot(token):
    try:
        bot = Bot(token=token)
        webhook_url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/{token}"
        cert = FSInputFile("webhook_cert.pem")
        await bot.set_webhook(url=webhook_url, certificate=cert, drop_pending_updates=True)
        logging.info(f"✅ Webhook set for Client Bot: {token[:10]}...")
        await bot.session.close()  # Memory မပြည့်စေရန် Session ကို သေချာပိတ်မည်
    except Exception as e:
        logging.error(f"❌ Failed to set webhook for {token[:10]}: {e}")

async def start_all_client_bots():
    logging.info("🔄 Setting Webhooks for all Client Bots from Database...")
    businesses = await db.businesses.find({"status": "active"}).to_list(length=1000)
    for biz in businesses:
        token = biz.get("bot_token")
        if token:
            await start_client_bot(token)
