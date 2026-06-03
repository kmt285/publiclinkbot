from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import AdminSetup

client_admin_router = Router()

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ငွေပေးချေမှု အကောင့်ထည့်ရန်", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Service အသစ်ထည့်ရန်", callback_data="add_service")]
    ])

@client_admin_router.callback_query(F.data == "set_payment")
async def set_payment_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
    await db.businesses.update_one({"bot_token": bot.token}, {"$set": {"payment_info": message.text}})
    await message.answer("✅ Ngwe pay chay hmu information updated successfully.")
    await state.clear()

# --- အဆင့် (၅) မှ ကုဒ်ဟောင်းများ ဆက်ရှိနေမည် (ကျဉ်းချထားပါသည်) ---
@client_admin_router.callback_query(F.data == "add_service")
async def add_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"): return
    await callback.message.answer("📝 ဝန်ဆောင်မှု (Service) အမည်ကို ရိုက်ထည့်ပါ။")
    await state.set_state(AdminSetup.waiting_for_service_name)
    await callback.answer()

@client_admin_router.message(AdminSetup.waiting_for_service_name)
async def receive_service_name(message: Message, state: FSMContext):
    await state.update_data(service_name=message.text)
    await message.answer("💰 ဤ Service အတွက် ဈေးနှုန်းကို ရိုက်ထည့်ပါ။")
    await state.set_state(AdminSetup.waiting_for_service_price)

@client_admin_router.message(AdminSetup.waiting_for_service_price)
async def receive_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(service_price=int(message.text))
    await message.answer("⏳ ဤ Service ၏ သက်တမ်း (ရက်အရေအတွက်) ကို ရိုက်ထည့်ပါ။ Lifetime အတွက် 0 ရိုက်ပါ။")
    await state.set_state(AdminSetup.waiting_for_service_duration)

@client_admin_router.message(AdminSetup.waiting_for_service_duration)
async def receive_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(service_duration=int(message.text))
    await message.answer("🔗 Private Group / Channel ID (သို့) Link ကို ရိုက်ထည့်ပါ။\n(မှတ်ချက် - တစ်ခါသုံးလင့်ခ်ထုတ်ပေးနိုင်ရန် Group ID ဥပမာ `-100123456789` သို့မဟုတ် `@channel_username` ကို ထည့်သွင်းပေးလျှင် ပိုကောင်းပါသည်)")
    await state.set_state(AdminSetup.waiting_for_service_link)

@client_admin_router.message(AdminSetup.waiting_for_service_link)
async def receive_service_link(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.services.insert_one({
        "bot_token": bot.token, "name": data['service_name'], "price": data['service_price'],
        "duration": data['service_duration'], "link": message.text, "status": "active"
    })
    await message.answer("✅ Service အသစ် အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!")
    await state.clear()

# ==========================================
# 💥 NEW: လုပ်ငန်းရှင် အတည်ပြု/ပယ်ချမှု ကို ကိုင်တွယ်ခြင်း
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
    
    # Link ကို အလိုအလျောက် ပြင်ဆင်ခြင်း
    chat_id_or_link = service.get("link")
    invite_link = chat_id_or_link
    
    # တကယ်လို့ Group ID (-100...) ထည့်ထားပြီး Bot က အဲဒီ Group ထဲမှာ Admin ဖြစ်နေပါက တစ်ခါသုံး Link ထုတ်ပေးမည်
    if chat_id_or_link.startswith("-100") or chat_id_or_link.startswith("@"):
        try:
            chat_member_link = await bot.create_chat_invite_link(chat_id=chat_id_or_link, member_limit=1)
            invite_link = chat_member_link.invite_link
        except Exception:
            pass # မအောင်မြင်ပါက ဖြည့်ထားသည့် စာသားအတိုင်း ပို့မည်
            
    # ဝယ်ယူသူထံ Group Link ပို့ပေးခြင်း
    user_id = subscription["user_id"]
    success_msg = (
        f"✅ **လူကြီးမင်း၏ ငွေပေးချေမှု အောင်မြင်ပါသည်။**\n\n"
        f"📦 **Service:** {service['name']}\n"
        f"⏳ **သက်တမ်း:** {'Lifetime (တစ်သက်လုံး)' if duration == 0 else f'{duration} ရက်'}\n\n"
        f"👇 အောက်ပါခလုတ်ကိုနှိပ်၍ Group/Channel သို့ ဝင်ရောက်နိုင်ပါပြီ။ (တစ်ခါသုံးလင့်ခ် ဖြစ်ပါသည်)"
    )
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Join Group / Channel", url=invite_link)]
    ])
    
    try:
        await bot.send_message(chat_id=user_id, text=success_msg, reply_markup=user_kb, parse_mode="Markdown")
    except Exception:
        pass
        
    # လုပ်ငန်းရှင်ထံ ပြန်ပြောင်းလဲပြသခြင်း
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 **Status: APPROVED (လက်ခံခဲ့ပြီး)**", reply_markup=None)
    await callback.answer("✅ အောင်မြင်စွာ လက်ခံပြီးပါပြီ။")

@client_admin_router.callback_query(F.data.startswith("sub_reject_"))
async def reject_subscription(callback: CallbackQuery, bot: Bot):
    sub_id = callback.data.split("_")[2]
    
    subscription = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    if not subscription or subscription.get("status") != "pending":
        await callback.answer("⚠️ ဤစာရင်းသည် ကိုင်တွယ်ပြီးသား ဖြစ်ပါသည်။", show_alert=True)
        return
        
    await db.subscriptions.update_one({"_id": ObjectId(sub_id)}, {"$set": {"status": "rejected"}})
    
    # ဝယ်ယူသူထံ ငြင်းပယ်ကြောင်း ပို့ခြင်း
    user_id = subscription["user_id"]
    reject_msg = "❌ **လူကြီးမင်း ပေးပို့ထားသော ငွေလွှဲပြေစာအား အတည်မပြုနိုင်ပါ။**\n\nကျေးဇူးပြု၍ ငွေလွှဲပမာဏနှင့် အချက်အလက်များ ပြန်လည်စစ်ဆေးပြီး `/start` နှိပ်ကာ ပြန်လည်ပေးပို့ပေးပါ။"
    try:
        await bot.send_message(chat_id=user_id, text=reject_msg)
    except Exception:
        pass
        
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **Status: REJECTED (ပယ်ချခဲ့ပြီး)**", reply_markup=None)
    await callback.answer("❌ ပယ်ချလိုက်ပြီးပါပြီ။")
