import asyncio
import logging
from aiogram import Bot, Dispatcher
from core.database import db
from handlers.client_bot import client_router
from handlers.client_admin import client_admin_router

# ==========================================
# 💥 NEW: Dispatcher နှင့် Router များကို Function အပြင်ဘက်တွင် တစ်ကြိမ်တည်းသာ ချိတ်ဆက်မည်
# ==========================================
client_dp = Dispatcher()
client_dp.include_router(client_router)
client_dp.include_router(client_admin_router)

async def start_client_bot(token):
    try:
        bot = Bot(token=token)
        # 💥 NEW: Dispatcher အသစ် ထပ်မလုပ်တော့ဘဲ အပေါ်က client_dp ဖြင့်သာ polling ကို တိုက်ရိုက်စတင်မည်
        asyncio.create_task(client_dp.start_polling(bot))
        logging.info(f"✅ Started Client Bot: {token[:10]}...")
    except Exception as e:
        logging.error(f"❌ Failed to start bot {token[:10]}: {e}")

async def start_all_client_bots():
    logging.info("🔄 Starting all Client Bots from Database...")
    businesses = await db.businesses.find({"status": "active"}).to_list(length=1000)
    for biz in businesses:
        token = biz.get("bot_token")
        if token:
            await start_client_bot(token)
