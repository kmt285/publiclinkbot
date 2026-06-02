# main.py
import os
import sys
import mimetypes
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web
import asyncio

# ==========================================================================
# ⚠️ ENVIRONMENT VARIABLES များကို ဘေးကင်းစွာ စစ်ဆေးဖတ်ရှုခြင်း
# ==========================================================================
try:
    API_ID = int(os.environ.get("API_ID", "0"))
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "0"))
except ValueError as e:
    print(f"❌ ENV ERROR: API_ID သို့မဟုတ် BIN_CHANNEL ကို Number အစစ်ပဲ ထည့်ရပါမည်။ စာသားများ မပါရပါ။ ({e})")
    sys.exit(1)

API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
APP_URL = os.environ.get("APP_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

# မရှိမဖြစ်လိုအပ်သော Variable များ ရှိမရှိ စစ်ဆေးခြင်း
if not API_ID or not API_HASH or not BOT_TOKEN or not BIN_CHANNEL:
    print("❌ CRITICAL ERROR: Environment Variables (API_ID, API_HASH, BOT_TOKEN, BIN_CHANNEL) မပြည့်စုံပါ။")
    print("💡 ဖြေရှင်းနည်း: Render Dashboard > Environment Tab ထဲတွင် Variable မူရင်းတန်ဖိုးများကို သေချာသွားထည့်ပေးပါ။")
    sys.exit(1)

# Telegram Bot Client စတင်ခြင်း
bot = Client("KMTStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
routes = web.RouteTableDef()

# ==========================================================================
# ၁။ TELEGRAM BOT LOGIC
# ==========================================================================
@bot.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def handle_incoming_file(client: Client, message: Message):
    try:
        forwarded = await message.forward(BIN_CHANNEL)
        msg_id = forwarded.id
        direct_link = f"{APP_URL}/file/{msg_id}"
        
        await message.reply_text(
            f"**✅ Direct Download / Stream Link ထုတ်ပေးပြီးပါပြီ**\n\n"
            f"🔗 **လင့်ခ်အမှန်:**\n`{direct_link}`\n\n"
            f"💡 ဤလင့်ခ်ကို မိမိ Blog ၏ Download Button တွင် ဖြစ်စေ၊ ဗီဒီယို Player တွင်ဖြစ်စေ တိုက်ရိုက်ထည့်သွင်းအသုံးပြုနိုင်ပါပြီခင်ဗျာ။",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")

# ==========================================================================
# ၂။ WEB SERVER LOGIC
# ==========================================================================
@routes.get("/file/{msg_id}")
async def stream_handler(request):
    msg_id = int(request.match_info["msg_id"])
    try:
        message = await bot.get_messages(BIN_CHANNEL, msg_id)
        media = message.document or message.video or message.audio or message.photo
        
        if not media:
            return web.Response(text="ဖိုင်ကို ရှာမတွေ့တော့ပါ။", status=404)
            
        file_name = getattr(media, "file_name", "image.png" if message.photo else "file.bin")
        file_size = media.file_size
        
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes"
        }
        
        response = web.StreamResponse(status=200, reason="OK", headers=headers)
        await response.prepare(request)
        
        async for chunk in bot.stream_media(media):
            await response.write(chunk)
            
        await response.write_eof()
        return response
    except Exception as e:
        return web.Response(text=f"Server Error: {str(e)}", status=500)

@routes.get("/")
async def home_page(request):
    return web.Response(text="KYAW MIN TUN - Direct File Stream Engine is securely running Live!")

# ==========================================================================
# ၃။ SERVER နှင့် BOT ကို စတင်ပတ်မည့်စနစ် (လုံခြုံရေး Try-Catch ခံထားသည်)
# ==========================================================================
async def main():
    print("🔄 Connecting to Telegram Servers...")
    try:
        await bot.start()
        print("✅ Telegram Bot Connected Successfully!")
    except Exception as e:
        print(f"❌ TELEGRAM CONNECTION FAILED: {e}")
        print("💡 အကြံပြုချက်: BOT_TOKEN, API_ID, API_HASH များကို မှန်ကန်မှု ရှိမရှိ ပြန်စစ်ပါ။")
        sys.exit(1)

    print("🔄 Starting Web Server...")
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    print(f"🚀 All Services are Live on Port {PORT}!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
