import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers.client_bot import client_router
from core.database import db

# Bot တစ်ခုချင်းစီကို Run မည့် Function
async def start_client_bot(token: str):
    try:
        bot = Bot(token=token)
        dp = Dispatcher()
        dp.include_router(client_router) # Client တွေရဲ့ Command များကို ချိတ်ဆက်ခြင်း
        
        logging.info(f"🚀 Starting Client Bot: {token[:10]}...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"❌ Failed to start bot {token[:10]}: {e}")

# Database ထဲရှိ Active ဖြစ်နေသော Bot အားလုံးကို တစ်ပြိုင်နက် Run မည့် Function
async def start_all_client_bots():
    cursor = db.businesses.find({"status": "active"})
    businesses = await cursor.to_list(length=100)
    
    for biz in businesses:
        token = biz.get("bot_token")
        if token:
            asyncio.create_task(start_client_bot(token))
