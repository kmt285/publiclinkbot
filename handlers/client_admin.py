from datetime import datetime, timedelta
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from utils.states import AdminSetup, AdminBroadcast, EditService
import asyncio

client_admin_router = Router()

# ==========================================
# 🛠 1. Admin Menu Keyboard
# ==========================================
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ငွေပေးချေမှု အကောင့်ထည့်ရန်", callback_data="set_payment")],
        [InlineKeyboardButton(text="➕ Service အသစ်ထည့်ရန်", callback_data="add_service")],
        [InlineKeyboardButton(text="⚙️ ဝန်ဆောင်မှုများ ပြင်/ဖျက်ရန်", callback_data="manage_services")],
        [InlineKeyboardButton(text="📢 အသုံးပြုသူများထံ Message ပို့ရန်", callback_data="broadcast_msg")]
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
    
    # 💥 Link မမေးမီ Note ကို အရင်မေးမည်
    await message.answer("📝 ဤ Service နှင့်ပတ်သက်သည့် မှတ်ချက်/ရှင်းလင်းချက် (Note) ကို ရိုက်ထည့်ပါ။\n(ဥပမာ - Daily 5 Signals, No refund, etc.)")
    await state.set_state(AdminSetup.waiting_for_service_note)

@client_admin_router.message(AdminSetup.waiting_for_service_note)
async def receive_service_note(message: Message, state: FSMContext):
    await state.update_data(service_note=message.text) # Note အား သိမ်းဆည်းခြင်း
    await message.answer("🔗 Private Group / Channel ID ကို ရိုက်ထည့်ပါ။\n(မှတ်ချက် - လုံခြုံသော ဝင်ခွင့်စနစ်သုံးရန် Group ID အတိအကျ ဥပမာ `-100123456789` ကို ထည့်သွင်းပါ။)")
    await state.set_state(AdminSetup.waiting_for_service_link)
    
@client_admin_router.message(AdminSetup.waiting_for_service_link)
async def receive_service_link(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    
    # DB ထဲသို့ သိမ်းဆည်းခြင်း (note ပါ ပေါင်းထည့်မည်)
    await db.services.insert_one({
        "bot_token": bot.token,
        "name": data['service_name'],
        "price": data['service_price'],
        "duration": data['service_duration'],
        "note": data['service_note'], # 💥 အသစ်ထည့်ရန်
        "link": message.text,
        "status": "active"
    })
    
    duration_val = data['service_duration']
    duration_text = "Lifetime (တစ်သက်လုံး)" if duration_val == 0 else f"{duration_val} ရက်"
    
    success_text = (
        "✅ **Service အသစ် အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!**\n\n"
        f"🔹 **အမည်:** {data['service_name']}\n"
        f"🔹 **ဈေးနှုန်း:** {data['service_price']} ကျပ်\n"
        f"🔹 **သက်တမ်း:** {duration_text}\n"
        f"📝 **မှတ်ချက် (Note):** {data['service_note']}\n" # 💥 အသစ်ထည့်ရန်
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


# ==========================================
# 📢 5. Broadcast System (လုပ်ငန်းရှင်များအတွက်)
# ==========================================
@client_admin_router.callback_query(F.data == "broadcast_msg")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"): return
    
    # 💥 စာသားကိုပါ ပြင်ဆင်လိုက်သည်
    await callback.message.answer("📢 Bot ကို လာရောက်အသုံးပြုဖူးသူ အားလုံးထံ ပို့မည့် စာသား၊ ဓာတ်ပုံ၊ ဗီဒီယို သို့မဟုတ် ပုံနှင့်စာ တွဲလျက် (Caption) ကို ယခု ပေးပို့ပါ။")
    await state.set_state(AdminBroadcast.waiting_for_msg)
    await callback.answer()

# 💥 NEW: မည်သည့် Media Type မဆို လက်ခံပြီး Copy ကူး၍ ပို့ဆောင်ပေးမည့် စနစ်
@client_admin_router.message(AdminBroadcast.waiting_for_msg)
async def do_broadcast(message: Message, state: FSMContext, bot: Bot):
    await message.answer("⏳ Message များကို စတင် ပို့ဆောင်နေပါပြီ။ ခေတ္တစောင့်ဆိုင်းပါ။...")
    await state.clear()
    
    # ဤ Bot တွင် ဝယ်ယူဖူးသူ/လာနှိပ်ဖူးသူ ID အားလုံးကို ထုတ်ယူခြင်း (ပုံစံမတူအောင် Unique ယူမည်)
    user_ids = await db.subscriptions.distinct("user_id", {"bot_token": bot.token})
    
    success_count = 0
    for u_id in user_ids:
        try:
            # 💥 send_message အစား copy_message ကို သုံးခြင်းဖြင့် Media မျိုးစုံကို ပို့နိုင်သည်
            await bot.copy_message(
                chat_id=u_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success_count += 1
            await asyncio.sleep(0.05) # Telegram Rate Limit မမိစေရန် ဖြည်းဖြည်းချင်းပို့မည်
        except Exception:
            pass # User မှ Bot ကို Block ထားပါက ကျော်သွားမည်
            
    await message.answer(f"✅ Message ပို့ဆောင်ခြင်း ပြီးဆုံးပါပြီ။\n📊 စုစုပေါင်း {success_count} ဦးထံသို့ အောင်မြင်စွာ ပို့ဆောင်နိုင်ခဲ့သည်။")
    
# ==========================================
# ⚙️ 6. Manage Services (ဝန်ဆောင်မှုများ ပြင်ဆင်/ဖျက်သိမ်းရန်)
# ==========================================
@client_admin_router.callback_query(F.data == "manage_services")
async def manage_services_list(callback: CallbackQuery, bot: Bot):
    business = await db.businesses.find_one({"bot_token": bot.token})
    if callback.from_user.id != business.get("owner_id"): return

    # Active ဖြစ်နေသော Service များကိုသာ ဆွဲထုတ်မည်
    services = await db.services.find({"bot_token": bot.token, "status": "active"}).to_list(length=100)
    
    if not services:
        await callback.answer("ဝန်ဆောင်မှု (Service) မရှိသေးပါ။", show_alert=True)
        return

    keyboard = []
    for s in services:
        keyboard.append([InlineKeyboardButton(text=f"⚙️ {s['name']}", callback_data=f"service_detail_{s['_id']}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menu သို့ ပြန်သွားရန်", callback_data="back_to_admin")])
    
    await callback.message.edit_text("⚙️ **ပြင်ဆင်/ဖျက်သိမ်း လိုသော ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@client_admin_router.callback_query(F.data == "back_to_admin")
async def back_to_admin_menu(callback: CallbackQuery):
    await callback.message.edit_text("🛠 **လုပ်ငန်းရှင် Admin Panel** မှ ကြိုဆိုပါတယ်။\n\nလိုအပ်သော လုပ်ဆောင်ချက်ကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။", reply_markup=admin_kb(), parse_mode="Markdown")

@client_admin_router.callback_query(F.data.startswith("service_detail_"))
async def show_service_detail(callback: CallbackQuery):
    service_id = callback.data.split("_")[2]
    service = await db.services.find_one({"_id": ObjectId(service_id)})
    
    if not service:
        await callback.answer("ဤ Service ကို ရှာမတွေ့တော့ပါ။", show_alert=True)
        return
        
    duration_val = service.get("duration", 0)
    duration_text = "Lifetime" if duration_val == 0 else f"{duration_val} ရက်"
    
    text = (
        f"📦 **Service အသေးစိတ်**\n\n"
        f"🔹 **အမည်:** {service['name']}\n"
        f"🔹 **ဈေးနှုန်း:** {service['price']} ကျပ်\n"
        f"🔹 **သက်တမ်း:** {duration_text}\n\n"
        f"📝 **မှတ်ချက် (Note):** {service.get('note', 'မရှိပါ')}\n\n"
        "အောက်ပါ လုပ်ဆောင်ချက်များထဲမှ ရွေးချယ်ပါ-"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ အမည် ပြင်မည်", callback_data=f"edit_name_{service_id}")],
        [InlineKeyboardButton(text="✏️ ဈေးနှုန်း ပြင်မည်", callback_data=f"edit_price_{service_id}")],
        [InlineKeyboardButton(text="✏️ မှတ်ချက် (Note) ပြင်မည်", callback_data=f"edit_note_{service_id}")],
        [InlineKeyboardButton(text="🗑 အပြီးတိုင် ဖျက်မည်", callback_data=f"delete_svc_{service_id}")],
        [InlineKeyboardButton(text="🔙 နောက်သို့", callback_data="manage_services")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@client_admin_router.callback_query(F.data.startswith("delete_svc_"))
async def delete_service(callback: CallbackQuery):
    service_id = callback.data.split("_")[2]
    
    # 💥 (အရေးကြီး) - Database ထဲမှ အပြီးတိုင်မဖျက်ဘဲ 'deleted' ဟုသာ ပြောင်းလိုက်မည်။
    # သို့မှသာ ယခင်ဝယ်ထားသော User များကို Auto-Kick စနစ်က ဆက်လက်အလုပ်လုပ်နိုင်မည် ဖြစ်သည်။
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"status": "deleted"}})
    
    await callback.answer("✅ ဝန်ဆောင်မှုကို အောင်မြင်စွာ ဖျက်သိမ်းပြီးပါပြီ။", show_alert=True)
    await manage_services_list(callback, callback.bot)

# --- ပြင်ဆင်ခြင်း (Edit Name / Edit Price) အပိုင်း ---
@client_admin_router.callback_query(F.data.startswith("edit_name_"))
async def ask_edit_name(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ ဝန်ဆောင်မှု၏ **အမည်အသစ်** ကို ရိုက်ထည့်ပါ။")
    await state.set_state(EditService.waiting_for_new_name)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_name)
async def save_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"name": message.text}})
    await message.answer("✅ ဝန်ဆောင်မှု အမည်ကို ပြင်ဆင်ပြီးပါပြီ။ Admin Panel သို့ ပြန်သွားရန် /start ကို နှိပ်ပါ။")
    await state.clear()

@client_admin_router.callback_query(F.data.startswith("edit_price_"))
async def ask_edit_price(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ ဝန်ဆောင်မှု၏ **ဈေးနှုန်းအသစ်** ကို ဂဏန်းဖြင့်သာ ရိုက်ထည့်ပါ။\n(ဥပမာ - 20000)")
    await state.set_state(EditService.waiting_for_new_price)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_price)
async def save_new_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။")
        return
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"price": int(message.text)}})
    await message.answer("✅ ဝန်ဆောင်မှု ဈေးနှုန်းကို ပြင်ဆင်ပြီးပါပြီ။ Admin Panel သို့ ပြန်သွားရန် /start ကို နှိပ်ပါ။")
    await state.clear()

# --- Note ပြင်ဆင်ခြင်း ---
@client_admin_router.callback_query(F.data.startswith("edit_note_"))
async def ask_edit_note(callback: CallbackQuery, state: FSMContext):
    service_id = callback.data.split("_")[2]
    await state.update_data(edit_svc_id=service_id)
    await callback.message.answer("✏️ ဝန်ဆောင်မှု၏ **မှတ်ချက် (Note) အသစ်** ကို ရိုက်ထည့်ပါ။\n(မှတ်ချက် မထားလိုပါက 'မရှိပါ' ဟု ရိုက်ထည့်နိုင်ပါသည်။)")
    await state.set_state(EditService.waiting_for_new_note)
    await callback.answer()

@client_admin_router.message(EditService.waiting_for_new_note)
async def save_new_note(message: Message, state: FSMContext):
    data = await state.get_data()
    service_id = data.get("edit_svc_id")
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": {"note": message.text}})
    await message.answer("✅ ဝန်ဆောင်မှု မှတ်ချက် (Note) ကို ပြင်ဆင်ပြီးပါပြီ။ Admin Panel သို့ ပြန်သွားရန် /start ကို နှိပ်ပါ။")
    await state.clear()
