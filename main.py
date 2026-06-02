# main.py
import os
import sys
import mimetypes
import asyncio

# ==========================================================================
# 🌟 PERFECT EVENT LOOP FIX FOR PYTHON 3.12 / 3.14
# ==========================================================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import web

# ==========================================================================
# ⚠️ ENVIRONMENT VARIABLES များကို ဖတ်ရှုခြင်း
# ==========================================================================
try:
    API_ID = int(os.environ.get("API_ID", "0"))
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "0"))
except ValueError as e:
    print(f"❌ ENV ERROR: API_ID သို့မဟုတ် BIN_CHANNEL ကို Number အစစ်ပဲ ထည့်ရပါမည်။ ({e})")
    sys.exit(1)

API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
APP_URL = os.environ.get("APP_URL", "")
PORT = int(os.environ.get("PORT", "8080"))

if not API_ID or not API_HASH or not BOT_TOKEN or not BIN_CHANNEL:
    print("❌ CRITICAL ERROR: Environment Variables မပြည့်စုံပါ။")
    sys.exit(1)

# Memory ပေါ်တွင် ပတ်မည့်စနစ်
bot = Client("KMTStreamBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
routes = web.RouteTableDef()

# ==========================================================================
# ၁။ TELEGRAM BOT LOGIC
# ==========================================================================

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "👋 **KYAW MIN TUN - File Stream Bot မှ ကြိုဆိုပါတယ်ဗျာ။**\n\n"
        "📁 ကျွန်တော့်ထံသို့ မည်သည့် ဖိုင်၊ ဓာတ်ပုံ၊ ဗီဒီယို သို့မဟုတ် အော်ဒီယိုမဆို ပေးပို့လိုက်ပါ။\n"
        "💡 သင့် Blog/Website ၏ Download Button တွင် တိုက်ရိုက်ထည့်သွင်းအသုံးပြုနိုင်မယ့် **Direct Link** ကို ချက်ချင်း ထုတ်ပေးသွားမှာ ဖြစ်ပါတယ်ခင်ဗျာ‌။",
        reply_to_message_id=message.id
    )

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def handle_incoming_file(client: Client, message: Message):
    try:
        reply_msg = await message.reply_text("🔄 Processing file... Please wait...", reply_to_message_id=message.id)
        
        # Log Channel သို့ Forward လှမ်းလုပ်မည်
        forwarded = await message.forward(BIN_CHANNEL)
        msg_id = forwarded.id
        direct_link = f"{APP_URL}/file/{msg_id}"
        
        await reply_msg.edit_text(
            f"**✅ Direct Download / Stream Link ထုတ်ပေးပြီးပါပြီ**\n\n"
            f"🔗 **လင့်ခ်အမှန်:**\n`{direct_link}`\n\n"
            f"💡 ဤလင့်ခ်ကို မိမိ Blog ၏ Download Button တွင် ဖြစ်စေ၊ ဗီဒီယို Player တွင်ဖြစ်စေ တိုက်ရိုက်ထည့်သွင်းအသုံးပြုနိုင်ပါပြီခင်ဗျာ။",
            disable_web_page_preview=True
        )
    except Exception as e:
        # Peer invalid ထပ်ဖြစ်ခဲ့ပါက အလုပ်လုပ်မည့် စမတ်ကျသော လမ်းညွှန်ချက်
        await message.reply_text(
            f"❌ **Error occurred:** {str(e)}\n\n"
            f"💡 **ဖြေရှင်းနည်းလမ်းညွှန်:**\n"
            f"ဆာဗာ Restart ဖြစ်သွားသောကြောင့် Channel နှင့် ခေတ္တအဆက်အသွယ်ပြတ်သွားခြင်း ဖြစ်နိုင်ပါသည်။\n\n"
            f"👉 ကျေးဇူးပြု၍ ခင်ဗျား၏ **Log Channel ထဲမှ ဖိုင်တစ်ခုခုကို ဤ Bot ထံသို့ တစ်ကြိမ်မျှ Forward လှမ်းပို့ပေးလိုက်ပါ**။ ၎င်းနောက် ဖိုင်များကို ပုံမှန်အတိုင်း ပြန်ပို့၍ လင့်ခ်ထုတ်ယူနိုင်ပါပြီဗျာ။"
        )

@bot.on_message(filters.private & filters.text)
async def text_guide(client: Client, message: Message):
    await message.reply_text(
        "ℹ️ **စာသား (Text) များကို လင့်ခ်ပြောင်းပေး၍ မရပါခင်ဗျာ။**\n\n"
        "ဒေါင်းလုဒ်လင့်ခ် ထုတ်ယူလိုသော ဖိုင်၊ ဗီဒီယို သို့မဟုတ် ဓာတ်ပုံများကိုသာ ပေးပို့ပေးပါဗျာ။"
    )

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
# ၃။ SERVER နှင့် BOT ကို စတင်ပတ်မည့်စနစ်
# ==========================================================================
async def main():
    print("🔄 Connecting to Telegram Servers...")
    try:
        await bot.start()
        print("✅ Telegram Bot Connected Successfully!")
    except Exception as e:
        print(f"❌ TELEGRAM CONNECTION FAILED: {e}")
        sys.exit(1)

    # 🌟 [FAILSAFE BUILD] စတင်ချိန်တွင် Channel ကို ဆွဲဖတ်မည်၊ အကယ်၍ မရခဲ့လျှင်ပင် ဆာဗာကို အကျဆုံးမခံဘဲ ဆက်ပတ်ထားမည့်စနစ် 🌟
    print(f"🔄 Attempting to pre-cache Log Channel ID: {BIN_CHANNEL}...")
    try:
        chat = await bot.get_chat(BIN_CHANNEL)
        print(f"✅ Success! Connected and Cached: '{chat.title}'")
    except Exception as cache_err:
        print(f"⚠️ Pre-cache Warning: {cache_err}")
        print("💡 စတင်ချိန်တွင် ကက်ရ်ှဆွဲရန် အခက်အခဲရှိသော်လည်း ဆာဗာပြိုကွဲမသွားစေရန် ဆက်လက်ပတ်ထားပါမည်။")

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
    loop.run_until_complete(main())
