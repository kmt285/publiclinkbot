import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web
from core.config import MASTER_BOT_TOKEN, PORT
from core.bot_manager import start_all_client_bots
from handlers.master_admin import master_router

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
    # ၁။ Web server စတင်ခြင်း
    asyncio.create_task(web_server())
    
    # ၂။ Master Bot Setup လုပ်ပြီး Run ခြင်း
    master_bot = Bot(token=MASTER_BOT_TOKEN)
    master_dp = Dispatcher()
    master_dp.include_router(master_router)
    
    logging.info("👑 Starting Master Bot...")
    asyncio.create_task(master_dp.start_polling(master_bot))
    
    # ၃။ Database ထဲရှိ လုပ်ငန်းရှင် Client Bots များအားလုံးကို Run ခြင်း
    logging.info("🔄 Starting all Client Bots from Database...")
    await start_all_client_bots()
    
    # System ကို မပိတ်သွားစေရန် ဆက်တိုက် Run ထားပေးခြင်း
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
