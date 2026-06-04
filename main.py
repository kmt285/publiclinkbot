import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web
from core.config import MASTER_BOT_TOKEN, PORT
from core.bot_manager import start_all_client_bots
from handlers.master_admin import master_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.scheduler import check_expired_subscriptions

logging.basicConfig(level=logging.INFO)

# Render အတွက် Dummy Web Server (Error မတက်စေရန်)
async def handle(request):
    return web.Response(text="SaaS Multi-Bot System is running smoothly on Render!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"🌐 Web server started on port {PORT}")

# Main Function (Bot များနှင့် Web Server တွဲ Run မည်)
async def main():
    asyncio.create_task(web_server())
    
    master_bot = Bot(token=MASTER_BOT_TOKEN)
    master_dp = Dispatcher()
    master_dp.include_router(master_router)
    
    logging.info("👑 Starting Master Bot...")
    asyncio.create_task(master_dp.start_polling(master_bot))
    
    logging.info("🔄 Starting all Client Bots from Database...")
    await start_all_client_bots()
    
    # 💥 NEW: Auto-Kick Scheduler ကို စတင်ခြင်း 💥
    scheduler = AsyncIOScheduler()
    # ဤနေရာတွင် ၁ နာရီတစ်ခါ စစ်ဆေးရန် သတ်မှတ်ထားသည် (စမ်းသပ်လိုပါက hours=1 အစား minutes=1 ဟု ပြင်နိုင်သည်)
    scheduler.add_job(check_expired_subscriptions, "interval", minutes=1) 
    scheduler.start()
    logging.info("⏱ Scheduler started for auto-kick system.")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
