from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import AdminSetup

client_admin_router = Router()

# ==========================================
# 🛠 1. Admin Menu Keyboard
# ==========================================
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ငွေပေးချေမှု အကောင့်ထည့်ရန်", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Service အသစ်ထည့်ရန်", callback_data="add_service")],
        [InlineKeyboardButton(text="📢 အသုံးပြုသူများထံ Message ပို့ရန် (Broadcast)", callback_data="broadcast_msg")] # ခလုတ်အသစ်
    ])

# ==========================================
# 💳 2. Payment Info Setup (ငွေပေးချေမှု အချက်အလက်)
# ==========================================
@client_admin_router.callback_query(F.data == "set_payment")
async def set_payment_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # လုံခြုံရေး - ပိုင်ရှင် ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"):
        await callback.answer("❌ သင်သည် ဤ Bot ၏ Admin မဟုတ်ပါ။", show_alert=True)
        return

    text = "💳 သင့်၏ ငွေပေးချေမှု အချက်အလက်များကို ရိုက်ထည့်ပါ။\n(ဥပမာ - KPay: 09123456789, Wave: 09987654321)"
    await callback.message.answer(text)
    await state.set_state(AdminSetup.waiting_for_payment_info)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_payment_info)
async def receive_payment_info(message: Message, bot: Bot, state: FSMContext):
    await db.businesses.update_one(
        {"bot_token": bot.token}, 
        {"$set": {"payment_info": message.text}}
    )
    await message.answer("✅ ငွေပေးချေမှု အချက်အလက်များကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။")
    await state.clear()

# ==========================================
# ➕ 3. Add New Service (Service အသစ် ဖန်တီးခြင်း)
# ==========================================
@client_admin_router.callback_query(F.data == "add_service")
async def add_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"):
        await callback.answer("❌ သင်သည် ဤ Bot ၏ Admin မဟုတ်ပါ။", show_alert=True)
        return

    await callback.message.answer("📝 ဝန်ဆောင်မှု (Service) အမည်ကို ရိုက်ထည့်ပါ။\n(ဥပမာ - VIP Trading Signals)")
    await state.set_state(AdminSetup.waiting_for_service_name)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_service_name)
async def receive_service_name(message: Message, state: FSMContext):
    await state.update_data(service_name=message.text)
    await message.answer("💰 ဤ Service အတွက် ဈေးနှုန်းကို ရိုက်ထည့်ပါ။\n(ဥပမာ - 15000)")
    await state.set_state(AdminSetup.waiting_for_service_price)

@client_admin_router.message(AdminSetup.waiting_for_service_price)
async def receive_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။ (ဥပမာ - 15000)")
        return
    await state.update_data(service_price=int(message.text))
    await message.answer("⏳ ဤ Service ၏ သက်တမ်း (ရက်အရေအတွက်) ကို ရိုက်ထည့်ပါ။\nတစ်သက်လုံး (Lifetime) သုံးခွင့်ပြုမည်ဆိုပါက 0 ဟု ရိုက်ထည့်ပါ။")
    await state.set_state(AdminSetup.waiting_for_service_duration)

@client_admin_router.message(AdminSetup.waiting_for_service_duration)
async def receive_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။ (ဥပမာ - 30)")
        return
    await state.update_data(service_duration=int(message.text))
    await message.answer("🔗 Private Group / Channel ID ကို ရိုက်ထည့်ပါ။\n(မှတ်ချက် - လုံခြုံသော ဝင်ခွင့်စနစ်သုံးရန် Group ID အတိအကျ ဥပမာ `-100123456789` ကို ထည့်သွင်းပါ။)")
    await state.set_state(AdminSetup.waiting_for_service_link)

@client_admin_router.message(AdminSetup.waiting_for_service_link)
async def receive_service_link(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    
    # DB ထဲသို့ သိမ်းဆည်းခြင်း
    await db.services.insert_one({
        "bot_token": bot.token,
        "name": data['service_name'],
        "price": data['service_price'],
        "duration": data['service_duration'],
        "link": message.text,
        "status": "active"
    })
    
    # 💥 Quote ငြိတဲ့ ပြဿနာမဖြစ်အောင် အပြင်မှာ ကြိုတင်ပြင်ဆင်ခြင်း
    duration_val = data['service_duration']
    duration_text = "Lifetime (တစ်သက်လုံး)" if duration_val == 0 else f"{duration_val} ရက်"
    
    success_text = (
        "✅ **Service အသစ် အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!**\n\n"
        f"🔹 **အမည်:** {data['service_name']}\n"
        f"🔹 **ဈေးနှုန်း:** {data['service_price']} ကျပ်\n"
        f"🔹 **သက်တမ်း:** {duration_text}\n"
        f"🔹 **Group/Link:** {message.text}"
    )
    await message.answer(success_text, parse_mode="Markdown")
    await state.clear()

# ==========================================
# ✅❌ 4. Slip Approval System (ငွေလွှဲပြေစာ အတည်ပြု/ပယ်ချ)
# ==========================================
@client_admin_router.callback_query(F.data.startswith("sub_approve_"))
async def approve_subscription(callback: CallbackQuery, bot: Bot):
    sub_id = callback.data.split("_")[2]
    
    subscription = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    if not subscription or subscription.get("status") != "pending":
        await callback.answer("⚠️ ဤစာရင်းသည် ကိုင်တွယ်ပြီးသား သို့မဟုတ် မရှိတော့ပါ။", show_alert=True)
        return
        
    service = await db.services.find_one({"_id": ObjectId(subscription["service_id"])})
    if not service:
        await callback.answer("❌ ဝန်ဆောင်မှု ရှာမတွေ့တော့ပါ။", show_alert=True)
        return
        
    # သက်တမ်း တွက်ချက်ခြင်း
    duration = service.get("duration", 0)
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=duration) if duration > 0 else None
        
    # Database တွင် Active ပြောင်းမည်
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {"status": "active", "start_date": start_date, "end_date": end_date}}
    )
    
    # Request to Join Link ထုတ်ပေးခြင်း
    chat_id_or_link = service.get("link")
    invite_link = chat_id_or_link
    
    if chat_id_or_link.startswith("-100") or chat_id_or_link.startswith("@"):
        try:
            chat_member_link = await bot.create_chat_invite_link(
                chat_id=chat_id_or_link, 
                creates_join_request=True, 
                name=f"User ID: {subscription['user_id']}"
            )
            invite_link = chat_member_link.invite_link
        except Exception as e:
            print(f"Error creating link: {e}")
            
    # ဝယ်ယူသူထံ အောင်မြင်ကြောင်းနှင့် Link ပို့ပေးခြင်း
    user_id = subscription["user_id"]
    success_msg = (
        f"✅ **လူကြီးမင်း၏ ငွေပေးချေမှု အောင်မြင်ပါသည်။**\n\n"
        f"📦 **Service:** {service['name']}\n"
        f"⏳ **သက်တမ်း:** {'Lifetime (တစ်သက်လုံး)' if duration == 0 else f'{duration} ရက်'}\n\n"
        f"👇 အောက်ပါခလုတ်ကိုနှိပ်၍ Group/Channel သို့ ဝင်ရောက်ရန် တောင်းဆိုပါ။"
    )
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Join Group / Channel", url=invite_link)]
    ])
    
    try:
        await bot.send_message(chat_id=user_id, text=success_msg, reply_markup=user_kb, parse_mode="Markdown")
    except Exception:
        pass # User က Bot ကို Block ထားလျှင် ကျော်သွားမည်
        
    # လုပ်ငန်းရှင်ထံ ပြန်ပြောင်းလဲပြသခြင်း (ခလုတ်များကို ဖျောက်မည်)
    new_caption = callback.message.caption + "\n\n🟢 **Status: APPROVED (လက်ခံခဲ့ပြီး)**"
    await callback.message.edit_caption(caption=new_caption, reply_markup=None)
    await callback.answer("✅ အောင်မြင်စွာ လက်ခံပြီးပါပြီ။")

@client_admin_router.callback_query(F.data.startswith("sub_reject_"))
async def reject_subscription(callback: CallbackQuery, bot: Bot):
    sub_id = callback.data.split("_")[2]
    
    subscription = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    if not subscription or subscription.get("status") != "pending":
        await callback.answer("⚠️ ဤစာရင်းသည် ကိုင်တွယ်ပြီးသား ဖြစ်ပါသည်။", show_alert=True)
        return
        
    # Database တွင် Rejected ပြောင်းမည်
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)}, 
        {"$set": {"status": "rejected"}}
    )
    
    # ဝယ်ယူသူထံ ငြင်းပယ်ကြောင်း ပို့ခြင်း
    user_id = subscription["user_id"]
    reject_msg = "❌ **လူကြီးမင်း ပေးပို့ထားသော ငွေလွှဲပြေစာအား အတည်မပြုနိုင်ပါ။**\n\nကျေးဇူးပြု၍ ငွေလွှဲပမာဏနှင့် အချက်အလက်များ ပြန်လည်စစ်ဆေးပြီး ဝန်ဆောင်မှုကို ပြန်လည်ရွေးချယ်ကာ Slip အသစ် ပေးပို့ပေးပါ။"
    
    try:
        await bot.send_message(chat_id=user_id, text=reject_msg, parse_mode="Markdown")
    except Exception:
        pass
        
    # လုပ်ငန်းရှင်ထံ ပြန်ပြောင်းလဲပြသခြင်း (ခလုတ်များကို ဖျောက်မည်)
    new_caption = callback.message.caption + "\n\n🔴 **Status: REJECTED (ပယ်ချခဲ့ပြီး)**"
    await callback.message.edit_caption(caption=new_caption, reply_markup=None)
    await callback.answer("❌ ပယ်ချလိုက်ပြီးပါပြီ။")

# 📢 5. Broadcast System (လုပ်ငန်းရှင်များအတွက်)
# ==========================================
from utils.states import AdminBroadcast
import asyncio

@client_admin_router.callback_query(F.data == "broadcast_msg")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"): return
    
    await callback.message.answer("📢 Bot ကို လာရောက်အသုံးပြုဖူးသူ အားလုံးထံ ပို့မည့် Message (စာသား) ကို ရိုက်ထည့်ပါ။")
    await state.set_state(AdminBroadcast.waiting_for_msg)
    await callback.answer()

@client_admin_router.message(AdminBroadcast.waiting_for_msg)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await message.answer("⏳ Message များကို စတင် ပို့ဆောင်နေပါပြီ။ ခေတ္တစောင့်ဆိုင်းပါ။...")
    await state.clear()
    
    # ဤ Bot တွင် ဝယ်ယူဖူးသူ/လာနှိပ်ဖူးသူ ID အားလုံးကို ထုတ်ယူခြင်း (ပုံစံမတူအောင် Unique ယူမည်)
    user_ids = await db.subscriptions.distinct("user_id", {"bot_token": bot.token})
    
    success_count = 0
    for u_id in user_ids:
        try:
            await bot.send_message(chat_id=u_id, text=message.text)
            success_count += 1
            await asyncio.sleep(0.05) # Telegram Rate Limit မမိစေရန် ဖြည်းဖြည်းချင်းပို့မည်
        except Exception:
            pass
            
    await message.answer(f"✅ Message ပို့ဆောင်ခြင်း ပြီးဆုံးပါပြီ။\n📊 စုစုပေါင်း {success_count} ဦးထံသို့ အောင်မြင်စွာ ပို့ဆောင်နိုင်ခဲ့သည်။")
