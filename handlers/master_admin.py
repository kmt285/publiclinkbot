import asyncio
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from bson.objectid import ObjectId
from core.database import db

master_router = Router()

@master_router.message(CommandStart())
async def start_cmd(message: Message):
    text = "👑 **SaaS Master Super Admin Bot** မှ ကြိုဆိုပါတယ်။\n\n"
    text += "🛠 **အသုံးပြုနိုင်သော အမိန့်စာများ:**\n"
    text += "👉 `/addbot <Bot_Token>` - လုပ်ငန်းရှင် Bot အသစ် ထည့်သွင်းရန်\n"
    text += "👉 `/stats` - စနစ်တစ်ခုလုံး၏ Data နှင့် လုပ်ငန်းရှင်များအား ကြည့်ရှုရန်"
    await message.answer(text, parse_mode="Markdown")

@master_router.message(Command("addbot"))
async def add_bot_cmd(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ ပုံစံမှားနေပါသည်။ \nဥပမာ - `/addbot 123456:ABC...`", parse_mode="Markdown")
        return
    
    token = args[1]
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        await message.answer("⚠️ ဒီ Bot Token က စနစ်ထဲမှာ ထည့်သွင်းပြီးသား ဖြစ်နေပါတယ်။")
        return

    await db.businesses.insert_one({
        "bot_token": token, 
        "status": "active",
        "owner_id": message.from_user.id 
    })
    
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    await message.answer("✅ Client Bot အသစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။ သင့် Bot ဆီသွား၍ /start ကိုနှိပ်ပါ။")

# ==========================================
# 📊 စနစ်တစ်ခုလုံးကို စောင့်ကြည့်မည့် Super Admin Panel
# ==========================================
@master_router.message(Command("stats"))
async def view_system_stats(message: Message):
    total_bots = await db.businesses.count_documents({})
    total_services = await db.services.count_documents({})
    active_users = await db.subscriptions.count_documents({"status": "active"})
    
    stats_text = (
        "📊 **SaaS System Overview (စာရင်းဇယား)**\n\n"
        f"🏢 **လုပ်ငန်းရှင် Bots:** {total_bots} ခု\n"
        f"📦 **စုစုပေါင်း Services:** {total_services} မျိုး\n"
        f"👥 **Active Users:** {active_users} ဦး\n\n"
        "စနစ်တစ်ခုလုံး တည်ငြိမ်စွာ လည်ပတ်နေပါသည်။ 🚀"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 လုပ်ငန်းရှင်များစာရင်း အသေးစိတ်ကြည့်ရန်", callback_data="view_businesses")]
    ])
    await message.answer(stats_text, reply_markup=kb, parse_mode="Markdown")

# --- လုပ်ငန်းရှင်များ စာရင်းပြသခြင်း ---
@master_router.callback_query(F.data == "view_businesses")
async def list_businesses(callback: CallbackQuery):
    businesses = await db.businesses.find({}).to_list(length=100)
    
    if not businesses:
        await callback.answer("လုပ်ငန်းရှင် မရှိသေးပါ။", show_alert=True)
        return

    keyboard = []
    for biz in businesses:
        token_prefix = biz['bot_token'][:10]
        # Bot အမည်ကို ခလုတ်တွင် ပြမည်
        keyboard.append([InlineKeyboardButton(text=f"🤖 Bot: {token_prefix}...", callback_data=f"biz_{str(biz['_id'])}")])
    
    await callback.message.edit_text(
        "🏢 **လုပ်ငန်းရှင်များ စာရင်း**\n\nအသေးစိတ်ကြည့်လိုသော Bot ကို ရွေးချယ်ပါ-", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )

# --- Bot တစ်ခုချင်းစီ၏ အသေးစိတ် အချက်အလက်များပြသခြင်း ---
@master_router.callback_query(F.data.startswith("biz_"))
async def view_business_detail(callback: CallbackQuery):
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if not biz:
        await callback.answer("အချက်အလက် ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = biz['bot_token']
    
    # နောက်ကွယ်မှ Bot ၏ Username ကို လှမ်းယူခြင်း
    try:
        temp_bot = Bot(token=token)
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close()
    except:
        bot_username = "Unknown"

    # ထို Bot အတွင်းရှိ Active User အရေအတွက် တွက်ခြင်း
    user_count = await db.subscriptions.count_documents({"bot_token": token, "status": "active"})
    
    # ထို Bot က ရောင်းချနေသော Service (Channel) များကို ယူခြင်း
    services = await db.services.find({"bot_token": token}).to_list(length=100)
    
    text = f"🤖 **Bot အမည်:** @{bot_username}\n"
    text += f"🔗 **Bot Link:** https://t.me/{bot_username}\n"
    text += f"👤 **Owner ID:** `{biz.get('owner_id', 'Unknown')}`\n"
    text += f"👥 **လက်ရှိ Active Users:** {user_count} ဦး\n\n"
    text += "📦 **Services & Channels:**\n"
    
    keyboard = []
    for s in services:
        text += f"🔹 {s['name']} (Price: {s['price']})\n"
        # Channel ID ဖြစ်ပါက Link ယူမည့် ခလုတ် ထည့်ပေးမည်
        if s['link'].startswith("-100") or s['link'].startswith("@"):
            keyboard.append([InlineKeyboardButton(text=f"🔗 '{s['name']}' Invite Link ယူရန်", callback_data=f"genlink_{str(s['_id'])}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="view_businesses")])
    
    await callback.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown", 
        disable_web_page_preview=True
    )

# --- Super Admin အတွက် Invite Link အလိုအလျောက် ထုတ်ပေးခြင်း ---
@master_router.callback_query(F.data.startswith("genlink_"))
async def generate_invite_link(callback: CallbackQuery):
    service_id = callback.data.split("_")[1]
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        await callback.answer("Service ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = service['bot_token']
    chat_id = service['link']
    
    try:
        temp_bot = Bot(token=token)
        # Super Admin ဝင်နိုင်ရန် One-Time Invite Link ထုတ်ပေးခြင်း
        link_obj = await temp_bot.create_chat_invite_link(chat_id=chat_id, member_limit=1)
        invite_link = link_obj.invite_link
        await temp_bot.session.close()
        
        await callback.answer()
        await callback.message.answer(
            f"✅ **{service['name']}** သို့ဝင်ရန် Invite Link ရရှိပါပြီ (တစ်ခါသုံး Link ဖြစ်ပါသည်) -\n{invite_link}",
            disable_web_page_preview=True
        )
    except Exception as e:
        await callback.answer("❌ Error: လုပ်ငန်းရှင်မှ ၎င်း၏ Group/Channel တွင် Bot အား Admin ခန့်ထားခြင်း မရှိသေးပါ။", show_alert=True)
