import asyncio
import logging
import ssl
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, TokenBasedRequestHandler, setup_application
from aiohttp import web
from core.config import MASTER_BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PORT
from core.bot_manager import start_all_client_bots, client_dp
from handlers.master_admin import master_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.scheduler import check_expired_subscriptions, check_business_expirations

logging.basicConfig(level=logging.INFO)

async def on_startup(app: web.Application):
    logging.info("🔄 Starting Webhook Server & Client Bots...")
    await start_all_client_bots()
    
    # Auto-Kick Scheduler
    scheduler = AsyncIOScheduler()
    master_bot = app["master_bot"]
    scheduler.add_job(check_expired_subscriptions, "interval", hours=1, next_run_time=datetime.now()) 
    scheduler.add_job(check_business_expirations, "interval", hours=1, args=[master_bot], next_run_time=datetime.now())
    scheduler.start()
    logging.info("⏱ Scheduler started for auto-kick system.")

async def main():
    # Bot ကို Event Loop အလုပ်လုပ်မှသာ စတင်ဖန်တီးမည်
    master_bot = Bot(token=MASTER_BOT_TOKEN)
    master_dp = Dispatcher()
    master_dp.include_router(master_router)
    
    app = web.Application()
    app["master_bot"] = master_bot
    
    # Master Bot အတွက် Webhook လမ်းကြောင်း
    master_webhook_path = "/webhook/master"
    master_handler = SimpleRequestHandler(dispatcher=master_dp, bot=master_bot)
    master_handler.register(app, path=master_webhook_path)
    
    # Client Bots များအတွက် Webhook လမ်းကြောင်း
    client_handler = TokenBasedRequestHandler(dispatcher=client_dp)
    client_handler.register(app, path="/webhook/{bot_token}")
    
    setup_application(app, master_dp, bot=master_bot)
    setup_application(app, client_dp)
    app.on_startup.append(on_startup)
    
    # Master Bot သို့ Webhook ချိတ်ဆက်ခြင်း
    webhook_url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}{master_webhook_path}"
    cert = FSInputFile("webhook_cert.pem")
    await master_bot.set_webhook(url=webhook_url, certificate=cert, drop_pending_updates=True)
    logging.info(f"👑 Master Bot Webhook set at {webhook_url}")

    # SSL Certificate အား Server တွင် တပ်ဆင်ခြင်း
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("webhook_cert.pem", "webhook_pkey.pem")
    
    # Web Server ကို Async ဖြင့် စနစ်တကျ Run ခြင်း
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=WEBHOOK_PORT, ssl_context=ssl_context)
    await site.start()
    
    logging.info(f"🌐 Webhook server is running on port {WEBHOOK_PORT}...")
    
    # 24/7 Run နေစေရန်
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
