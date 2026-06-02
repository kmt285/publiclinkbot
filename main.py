# main.py
import os
import mimetypes
from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web
import asyncio

API_ID = int(os.environ.get("API_ID", "1234567"))       
API_HASH = os.environ.get("API_HASH", "your_api_hash")     
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")   
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-100xxx")) 
APP_URL = os.environ.get("APP_URL", "https://your-bot.onrender.com")
PORT = int(os.environ.get("PORT", "8080"))

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
# ၂။ WEB SERVER LOGIC (ဖိုင်များကို Chunks အလိုက် စီးဆင်းစေခြင်း - Stream စနစ်)
# ==========================================================================
@routes.get("/file/{msg_id}")
async def stream_handler(request):
    msg_id = int(request.match_info["msg_id"])
    
    try:
        # Log Channel ထဲမှ ဖိုင်ကို သတ်မှတ်ထားသော Message ID ဖြင့် သွားရှာမည်
        message = await bot.get_messages(BIN_CHANNEL, msg_id)
        media = message.document or message.video or message.audio or message.photo
        
        if not media:
            return web.Response(text="ဖိုင်ကို ရှာမတွေ့တော့ပါ သို့မဟုတ် ဖျက်ပစ်လိုက်ပါပြီ။", status=404)
            
        file_name = getattr(media, "file_name", "image.png" if message.photo else "file.bin")
        file_size = media.file_size
        
        # Extension ကိုကြည့်ပြီး Browser မှ တိုက်ရိုက်ဖွင့်နိုင်ရန် MIME Type သတ်မှတ်ခြင်း
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        # Headers သတ်မှတ်ခြင်း (Accept-Ranges ပါဝင်သဖြင့် ဗီဒီယိုများကို အရှေ့အနောက် ဆွဲကြည့်၍ရပါသည်)
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes"
        }
        
        response = web.StreamResponse(status=200, reason="OK", headers=headers)
        await response.prepare(request)
        
        # 🌟 အရေးကြီးဆုံးအပိုင်း: Telegram ဆာဗာမှ ဖိုင် chunks များကို တိုက်ရိုက်ဆွဲယူပြီး Browser ဆီ stream ပို့ပေးခြင်း
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
# ၃။ SERVER နှင့် BOT ကို တစ်ပြိုင်တည်း အတူ Run စေမည့်စနစ်
# ==========================================================================
async def main():
    await bot.start()
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print("🚀 Bot & Stream Server started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
