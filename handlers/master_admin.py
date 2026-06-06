import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import MasterSetup
from utils.states import MasterBooking

master_router = Router()

# ==========================================
# 💥 Render Environment Variable မှ Super Admin ID များကို ဆွဲယူခြင်း
# ==========================================
admin_ids_str = os.getenv("SUPER_ADMIN_IDS", "")
SUPER_ADMINS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]

@master_router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
    # 👑 Super Admin ဝင်လာလျှင်
    if message.from_user.id in SUPER_ADMINS:
        text = "👑 **SaaS Master Super Admin Bot** မှ ကြိုဆိုပါတယ်။\n\n"
        text += "သင်သည် Super Admin ဖြစ်သောကြောင့် အောက်ပါ ခလုတ်ကိုနှိပ်၍ စနစ်တစ်ခုလုံးကို စီမံနိုင်ပါသည်။"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 စနစ်တစ်ခုလုံး၏ စာရင်းဇယားကြည့်ရန်", callback_data="show_stats")]
        ])
        return await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    
    # 🏢 သာမန် လုပ်ငန်းရှင် ဝင်လာလျှင်
    biz = await db.businesses.find_one({"owner_id": message.from_user.id})
    
    if not biz:
        text = "🌟 **SaaS Telegram Bot Platform** မှ ကြိုဆိုပါတယ်။\n\nလူကြီးမင်း၏ ကိုယ်ပိုင် VIP Subscription Bot ကို (၁) လ အခမဲ့ စတင်အသုံးပြုနိုင်ရန် အောက်ပါခလုတ်ကို နှိပ်ပါ။"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Bot အသစ် ဖန်တီးရန်", callback_data="create_new_bot")]])
        return await message.answer(text, reply_markup=kb, parse_mode="Markdown")
        
    # သက်တမ်းတွက်ချက်ခြင်း
    exp = biz.get("expires_at")
    if not exp:
        exp_text = "Lifetime (အကန့်အသတ်မရှိ)"
        status_text = "🟢 Active"
    else:
        exp_text = exp.strftime("%d-%m-%Y")
        status_text = "🔴 Suspended (ရပ်ဆိုင်းထားသည်)" if biz.get("status") == "suspended" else "🟢 Active"
        
    text = (
        f"🏢 **လူကြီးမင်း၏ Bot အချက်အလက်များ**\n\n"
        f"🤖 **Bot Token:** `{biz['bot_token'][:15]}...`\n"
        f"⏳ **သက်တမ်းကုန်ဆုံးမည့်ရက်:** {exp_text}\n"
        f"📊 **အခြေအနေ:** {status_text}\n\n"
        "💳 **သက်တမ်းတိုးရန် အောက်ပါ Plan များမှ တစ်ခုကို ရွေးချယ်ပါ။**"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 1 Month Plan - 30,000 MMK", callback_data="buyplan_30")],
        [InlineKeyboardButton(text="🔹 3 Months Plan - 80,000 MMK", callback_data="buyplan_90")],
        [InlineKeyboardButton(text="🔹 6 Months Plan - 150,000 MMK", callback_data="buyplan_180")],
        [InlineKeyboardButton(text="💎 Lifetime Plan - 500,000 MMK", callback_data="buyplan_0")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
# ==========================================
# 🏢 လုပ်ငန်းရှင်များ Bot Token ထည့်သွင်းခြင်း စနစ်
# ==========================================
@master_router.callback_query(F.data == "create_new_bot")
async def ask_bot_token(callback: CallbackQuery, state: FSMContext):
    text = "🤖 **Bot Token ထည့်သွင်းပါ**\n\n"
    text += "1. @BotFather သို့သွား၍ `/newbot` ဖြင့် Bot အသစ်တစ်ခု ဖန်တီးပါ။\n"
    text += "2. ရရှိလာသော **HTTP API Token** (ဥပမာ `123456:ABC-DEF...`) ကို ဤနေရာတွင် Copy/Paste လုပ်ပါ။"
    await callback.message.answer(text, parse_mode="Markdown")
    await state.set_state(MasterSetup.waiting_for_bot_token)
    await callback.answer()

@master_router.message(MasterSetup.waiting_for_bot_token)
async def receive_bot_token(message: Message, state: FSMContext):
    token = message.text.strip()
    
    # Token အကြမ်းဖျင်း မှန်/မမှန် စစ်ဆေးခြင်း
    if ":" not in token:
        return await message.answer("❌ Token ပုံစံ မှားယွင်းနေပါသည်။ သေချာစွာ ပြန်လည်စစ်ဆေးပြီး ထပ်မံရိုက်ထည့်ပါ။")
        
    existing_bot = await db.businesses.find_one({"bot_token": token})
    if existing_bot:
        return await message.answer("⚠️ ဤ Bot Token မှာ စနစ်ထဲတွင် ထည့်သွင်းပြီးသား ဖြစ်နေပါသည်။")

    await message.answer("⏳ Bot Token အား စစ်ဆေးနေပါသည်... ခေတ္တစောင့်ဆိုင်းပါ။")

    # 💥 NEW: Token အစစ်အမှန် ဟုတ်/မဟုတ် Telegram သို့ လှမ်း၍ စစ်ဆေးခြင်း 💥
    try:
        temp_bot = Bot(token=token)
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close() # စစ်ဆေးပြီးပါက ပြန်ပိတ်မည်
    except Exception as e:
        return await message.answer("❌ **Bot Token အမှားဖြစ်နေပါသည်။** (သို့မဟုတ်) ပိတ်ပင်ခံထားရသော Bot ဖြစ်နေပါသည်။\n\nကျေးဇူးပြု၍ @BotFather မှ Token အမှန်ကိုသာ Copy ကူး၍ ထပ်မံရိုက်ထည့်ပါ။")

    # မှန်ကန်ပါက ဆက်လက်အလုပ်လုပ်မည်
    created_date = datetime.utcnow()
    expires_date = created_date + timedelta(days=30)

    await db.businesses.insert_one({
        "bot_token": token, 
        "status": "active",
        "owner_id": message.from_user.id,
        "owner_username": message.from_user.username, 
        "created_at": created_date,
        "expires_at": expires_date
    })
    
    from core.bot_manager import start_client_bot 
    asyncio.create_task(start_client_bot(token))
    
    success_text = f"✅ **Client Bot (@{bot_username}) အသစ် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။**\n\n"
    success_text += "🎁 ဤ Bot အား (၁) လ အခမဲ့ အသုံးပြုခွင့် ပေးထားပါသည်။\n"
    success_text += f"👉 ယခု သင့် Bot ( https://t.me/{bot_username} ) ဆီသွား၍ `/start` ကိုနှိပ်ပြီး ဝန်ဆောင်မှုများကို စတင် ဖန်တီးနိုင်ပါပြီ။"
    await message.answer(success_text, parse_mode="Markdown")
    await state.clear()

# ==========================================
# 📊 စနစ်တစ်ခုလုံးကို စောင့်ကြည့်မည့် Super Admin Panel (Admin သီးသန့်)
# ==========================================
@master_router.callback_query(F.data == "show_stats")
async def view_system_stats_cb(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return # 💥 လုံခြုံရေး ပိတ်ပင်ခြင်း
    
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
        [InlineKeyboardButton(text="🏢 လုပ်ငန်းရှင်များစာရင်း အသေးစိတ်ကြည့်ရန်", callback_data="view_businesses")],
        [InlineKeyboardButton(text="🧹 Database အမှိုက်များ ရှင်းလင်းမည်", callback_data="clean_database")] 
    ])
    await callback.message.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")

# --- လုပ်ငန်းရှင်များ စာရင်းပြသခြင်း ---
@master_router.callback_query(F.data == "view_businesses")
async def list_businesses(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    businesses = await db.businesses.find({}).to_list(length=100)
    
    if not businesses:
        await callback.answer("လုပ်ငန်းရှင် မရှိသေးပါ။", show_alert=True)
        return

    keyboard = []
    for biz in businesses:
        token_prefix = biz['bot_token'][:10]
        keyboard.append([InlineKeyboardButton(text=f"🤖 Bot: {token_prefix}...", callback_data=f"biz_{str(biz['_id'])}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="show_stats")])
    
    await callback.message.edit_text(
        "🏢 **လုပ်ငန်းရှင်များ စာရင်း**\n\nအသေးစိတ်ကြည့်လိုသော Bot ကို ရွေးချယ်ပါ-", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="Markdown"
    )

# --- Bot တစ်ခုချင်းစီ၏ အသေးစိတ် အချက်အလက်များပြသခြင်း ---
@master_router.callback_query(F.data.startswith("biz_"))
async def view_business_detail(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if not biz:
        await callback.answer("အချက်အလက် ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = biz['bot_token']
    
    try:
        temp_bot = Bot(token=token)
        me = await temp_bot.get_me()
        bot_username = me.username
        await temp_bot.session.close()
    except:
        bot_username = "Unknown"

    user_count = await db.subscriptions.count_documents({"bot_token": token, "status": "active"})
    services = await db.services.find({"bot_token": token, "status": "active"}).to_list(length=100)
    
    is_suspended = biz.get("status") == "suspended"
    expires_at = biz.get("expires_at")
    
    if is_suspended:
        status_text = "🚫 Suspended (အက်ဒမင်မှ ရပ်ဆိုင်းထားသည်)"
        toggle_btn = "🟢 Bot အား ပြန်ဖွင့်ပေးမည်"
    elif expires_at:
        is_expired = datetime.utcnow() > expires_at
        exp_date_str = expires_at.strftime("%d-%m-%Y")
        status_text = "🔴 Expired (သက်တမ်းကုန်နေပါသည်)" if is_expired else f"🟢 Active (Exp: {exp_date_str})"
        toggle_btn = "🚫 Bot အား ရပ်ဆိုင်းမည် (Suspend)"
    else:
        status_text = "🟢 Active (Unlimited)"
        toggle_btn = "🚫 Bot အား ရပ်ဆိုင်းမည် (Suspend)"

    o_username = biz.get('owner_username')
    owner_display = f"@{o_username}" if o_username else "မသိရှိပါ"

    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    text = f"🤖 <b>Bot အမည်:</b> @{bot_username}\n"
    text += f"🔗 <b>Bot Link:</b> https://t.me/{bot_username}\n"
    text += f"👤 <b>Owner:</b> {owner_display} (ID: <code>{biz.get('owner_id', 'Unknown')}</code>)\n"
    text += f"👥 <b>လက်ရှိ Active Users:</b> {user_count} ဦး\n"
    text += f"⏳ <b>Bot အခြေအနေ:</b> {status_text}\n\n"
    text += "📦 <b>Services & Channels:</b>\n"
    
    keyboard = []
    for s in services:
        text += f"🔹 {s['name']} (Price: {s['price']})\n"
        if s['link'].startswith("-100") or s['link'].startswith("@"):
            keyboard.append([InlineKeyboardButton(text=f"🔗 '{s['name']}' Invite Link ယူရန်", callback_data=f"genlink_{str(s['_id'])}")])
    
    keyboard.append([InlineKeyboardButton(text=toggle_btn, callback_data=f"togglebot_{str(biz['_id'])}")])
    keyboard.append([InlineKeyboardButton(text="🗑 Bot အား အပြီးတိုင် ဖျက်သိမ်းမည်", callback_data=f"harddelete_{str(biz['_id'])}")])
    keyboard.append([InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="view_businesses")])
    
    # 💥 parse_mode="HTML" ဟု ပြောင်းထားသည်
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML", disable_web_page_preview=True)

# --- Super Admin အတွက် Invite Link အလိုအလျောက် ထုတ်ပေးခြင်း ---
@master_router.callback_query(F.data.startswith("genlink_"))
async def generate_invite_link(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    service_id = callback.data.split("_")[1]
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        await callback.answer("Service ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    token = service['bot_token']
    chat_id = service['link']
    
    try:
        temp_bot = Bot(token=token)
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

# --- Bot ရပ်ဆိုင်းသည့် ကုဒ် ---
@master_router.callback_query(F.data.startswith("togglebot_"))
async def toggle_business_bot(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if not biz:
        return
        
    new_status = "suspended" if biz.get("status") == "active" else "active"
    
    await db.businesses.update_one({"_id": ObjectId(biz_id)}, {"$set": {"status": new_status}})
    
    msg = "🚫 Bot အား အောင်မြင်စွာ ရပ်ဆိုင်းလိုက်ပါပြီ。" if new_status == "suspended" else "🟢 Bot အား အောင်မြင်စွာ ပြန်ဖွင့်ပေးလိုက်ပါပြီ。"
    await callback.answer(msg, show_alert=True)
    
    await callback.message.edit_text(f"{msg}\n\nအပြောင်းအလဲအား မြင်တွေ့ရရန် နောက်သို့ပြန်ထွက်ပြီး ပြန်ဝင်ကြည့်ပါ။", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 စာရင်းများသို့ ပြန်သွားရန်", callback_data="view_businesses")]]))

# ==========================================
# 🧹 Database ရှင်းလင်းရေး (Clean Database - 7 Days Grace Period)
# ==========================================
@master_router.callback_query(F.data == "clean_database")
async def clean_database_handler(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    await callback.message.edit_text("⏳ **Database အား စတင် ရှင်းလင်းနေပါသည်...**\nခေတ္တစောင့်ဆိုင်းပါ။")
    
    # ၁။ (၇) ရက် ကျော်လွန်သွားသော သက်တမ်းကုန် Bot များ၏ Data များကို ရှင်းလင်းမည် (Token ကို ချန်ထားမည်)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    expired_businesses = await db.businesses.find({"expires_at": {"$lt": seven_days_ago}}).to_list(length=1000)
    
    cleaned_bots_count = 0
    for biz in expired_businesses:
        token = biz["bot_token"]
        # ထို Bot နှင့်သက်ဆိုင်သော Service နှင့် Subscription အားလုံးကို ရှင်းလင်းမည်
        await db.services.delete_many({"bot_token": token})
        await db.subscriptions.delete_many({"bot_token": token})
        cleaned_bots_count += 1

    # ၂။ ငြင်းပယ်ခံထားရသော (Rejected) စာရင်းဟောင်းများကို ရှင်းလင်းမည်
    del_rejected = await db.subscriptions.delete_many({"status": "rejected"})
    
    text = (
        "✅ **Database ရှင်းလင်းခြင်း အောင်မြင်ပါသည်။**\n\n"
        f"🧹 သက်တမ်း (၇) ရက်ကျော်လွန်သွားသော Bot ပေါင်း **{cleaned_bots_count}** ခု၏ Services နှင့် Users များကို ရှင်းလင်းပြီးပါပြီ။\n*(မှတ်ချက် - ၎င်းတို့၏ Bot Token များကိုမူ ဆက်လက် ထိန်းသိမ်းထားပါသည်)*\n\n"
        f"🗑 ပယ်ချထားသော (Rejected) ပြေစာဟောင်း **{del_rejected.deleted_count}** ခုကို ရှင်းလင်းပြီးပါပြီ။"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 စာရင်းဇယားသို့ ပြန်သွားရန်", callback_data="show_stats")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# ==========================================
# 🗑 အပြီးတိုင် ဖျက်သိမ်းခြင်း (Hard Delete)
# ==========================================
@master_router.callback_query(F.data.startswith("harddelete_"))
async def hard_delete_bot(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMINS: return 
    
    biz_id = callback.data.split("_")[1]
    biz = await db.businesses.find_one({"_id": ObjectId(biz_id)})
    
    if biz:
        token = biz["bot_token"]
        # Database ထဲမှ ဤ Bot နှင့် ပတ်သက်သမျှ အရာအားလုံးကို အမြစ်ပြတ် ရှင်းထုတ်မည်
        await db.businesses.delete_one({"_id": ObjectId(biz_id)})
        await db.services.delete_many({"bot_token": token})
        await db.subscriptions.delete_many({"bot_token": token})
        
    await callback.answer("✅ Bot အား Database မှ အပြီးတိုင် ဖျက်သိမ်းလိုက်ပါပြီ။", show_alert=True)
    
    # ရှင်းပြီးပါက လုပ်ငန်းရှင်များစာရင်းသို့ ပြန်သွားမည်
    await list_businesses(callback)

# 💳 Master Payment Info (Super Admin မှ သတ်မှတ်ရန်)
# ==========================================
@master_router.message(Command("setpayment"))
async def set_master_payment(message: Message):
    if message.from_user.id not in SUPER_ADMINS: return
    
    pay_info = message.text.replace("/setpayment", "").strip()
    if not pay_info:
        return await message.answer("❌ ပုံစံမှားနေပါသည်။\nအသုံးပြုရန်: `/setpayment KPay - 09123456789 (U Mya)`", parse_mode="Markdown")
        
    await db.system_config.update_one(
        {"_id": "master_config"}, 
        {"$set": {"payment_info": pay_info}}, 
        upsert=True
    )
    await message.answer(f"✅ လုပ်ငန်းရှင်များ ငွေလွှဲရန် အကောင့်ကို အောင်မြင်စွာ မှတ်သားပြီးပါပြီ။\n\n{pay_info}")

# ==========================================
# 🛍 လုပ်ငန်းရှင်များ Subscription ဝယ်ယူခြင်း (Renew Plans)
# ==========================================
@master_router.callback_query(F.data.startswith("buyplan_"))
async def buy_master_plan(callback: CallbackQuery, state: FSMContext):
    days = int(callback.data.split("_")[1])
    
    config = await db.system_config.find_one({"_id": "master_config"})
    pay_info = config.get("payment_info", "ငွေပေးချေမှု အချက်အလက် မရှိသေးပါ။ Super Admin ထံ ဆက်သွယ်ပါ။") if config else "Admin ထံ ဆက်သွယ်ပါ။"
    
    plan_names = {30: "၁ လ (30 Days)", 90: "၃ လ (90 Days)", 180: "၆ လ (180 Days)", 0: "တစ်သက်လုံး (Lifetime)"}
    prices = {30: "30,000", 90: "80,000", 180: "150,000", 0: "500,000"} # 💥 ဤနေရာတွင် ဈေးနှုန်းများ ပြင်နိုင်သည်
    
    text = (
        f"💳 **'{plan_names[days]}' သက်တမ်းတိုးရန် ငွေလွှဲရမည့် အချက်အလက်**\n\n"
        f"🏦 **အကောင့်:** {pay_info}\n"
        f"💵 **ကျသင့်ငွေ:** {prices[days]} ကျပ်\n\n"
        "⚠️ **အရေးကြီးသည်:** ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Slip Screenshot) ကို ဤနေရာသို့ ဓာတ်ပုံ (Photo) အဖြစ် ပို့ပေးပါ။"
    )
    
    await state.update_data(plan_days=days)
    await state.set_state(MasterBooking.waiting_for_slip)
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@master_router.message(MasterBooking.waiting_for_slip, F.photo)
async def receive_master_slip(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    days = data.get("plan_days")
    photo_id = message.photo[-1].file_id
    
    await message.answer("⏳ ငွေလွှဲပြေစာကို လက်ခံရရှိပါပြီ။ Super Admin မှ အတည်ပြုပြီးပါက သက်တမ်း အလိုအလျောက် တိုးသွားပါမည်။")
    await state.clear()
    
    # Super Admin များထံသို့ ပြေစာလှမ်းပို့မည်
    plan_names = {30: "၁ လ", 90: "၃ လ", 180: "၆ လ", 0: "Lifetime"}
    admin_text = (
        f"💰 **လုပ်ငန်းရှင်ထံမှ သက်တမ်းတိုး ပြေစာ ရောက်ရှိလာပါသည်!**\n\n"
        f"👤 **လုပ်ငန်းရှင်:** {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"📦 **Plan:** {plan_names[days]}\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Approve (အတည်ပြုမည်)", callback_data=f"master_approve_{message.from_user.id}_{days}")],
        [InlineKeyboardButton(text="❌ Reject (ပယ်ချမည်)", callback_data=f"master_reject_{message.from_user.id}")]
    ])
    
    for admin_id in SUPER_ADMINS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=admin_text, reply_markup=kb, parse_mode="Markdown")
        except: pass

# --- Super Admin မှ Approve / Reject ပြုလုပ်ခြင်း ---
@master_router.callback_query(F.data.startswith("master_approve_"))
async def approve_business_sub(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    
    parts = callback.data.split("_")
    owner_id = int(parts[2])
    days = int(parts[3])
    
    biz = await db.businesses.find_one({"owner_id": owner_id})
    if not biz:
        return await callback.answer("ဤလုပ်ငန်းရှင် ရှာမတွေ့ပါ။", show_alert=True)
        
    now = datetime.utcnow()
    current_exp = biz.get("expires_at")
    
    if days == 0:
        new_exp = None # Lifetime
    else:
        if current_exp and current_exp > now:
            new_exp = current_exp + timedelta(days=days) # ရှိရင်းစွဲသက်တမ်းပေါ် ထပ်ပေါင်းမည်
        else:
            new_exp = now + timedelta(days=days) # သက်တမ်းကုန်နေပါက ယနေ့မှစ၍ ပေါင်းမည်
            
    await db.businesses.update_one(
        {"owner_id": owner_id},
        {"$set": {
            "expires_at": new_exp, 
            "status": "active",
            "notified_7": False, "notified_3": False, "notified_1": False # သတိပေးချက်များကို Reset ချမည်
        }}
    )
    
    # လုပ်ငန်းရှင်ထံ အကြောင်းကြားမည်
    try:
        await bot.send_message(owner_id, "✅ **ဂုဏ်ယူပါသည်။ လူကြီးမင်း၏ Bot သက်တမ်းတိုးခြင်း အောင်မြင်ပါသည်။**\n\nစနစ်အား ပုံမှန်အတိုင်း ပြန်လည်အသုံးပြုနိုင်ပါပြီ။", parse_mode="Markdown")
    except: pass
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 **APPROVED**", reply_markup=None)
    await callback.answer("သက်တမ်းတိုးပေးလိုက်ပါပြီ။")

@master_router.callback_query(F.data.startswith("master_reject_"))
async def reject_business_sub(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in SUPER_ADMINS: return
    owner_id = int(callback.data.split("_")[2])
    
    try:
        await bot.send_message(owner_id, "❌ **လူကြီးမင်း၏ ငွေလွှဲပြေစာအား အတည်မပြုနိုင်ပါ။**\n\nကျေးဇူးပြု၍ ပြေစာအမှန်အား ပြန်လည်စစ်ဆေး၍ အသစ်ပေးပို့ပေးပါ။", parse_mode="Markdown")
    except: pass
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **REJECTED**", reply_markup=None)
