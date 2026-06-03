import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from core.database import db

master_router = Router()

@master_router.message(CommandStart())
async def start_cmd(message: Message):
    text = "မင်္ဂလာပါ။ SaaS Master Bot မှ ကြိုဆိုပါတယ်။ 👑\n\n"
    text += "လုပ်ငန်းရှင် Bot အသစ်ထည့်ရန် အောက်ပါအတိုင်း ရိုက်ထည့်ပါ-\n"
    text += "👉 `/addbot <Bot_Token>`"
    await message.answer(text, parse_mode="Markdown")

@master_router.message(Command("addbot"))
async def add_bot_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ ပုံစံမှားနေပါသည်။ \nဥပမာ - `/addbot 123456:ABCDEFGHIJK...`", parse_mode="Markdown")
        return
    
    token = args[1]
    
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        await message.answer("⚠️ ဒီ Bot Token က စနစ်ထဲမှာ ထည့်သွင်းပြီးသား ဖြစ်နေပါတယ်။")
        return

    # 💥 ဒီနေရာမှာ လာထည့်တဲ့သူရဲ့ ID ကို owner_id အနေနဲ့ မှတ်လိုက်ပါပြီ
    await db.businesses.insert_one({
        "bot_token": token, 
        "status": "active",
        "owner_id": message.from_user.id 
    })
    
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    await message.answer("✅ Client Bot အသစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။ သင့် Bot ဆီသွား၍ /start ကိုနှိပ်ပါ။")
