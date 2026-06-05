from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bson.objectid import ObjectId
from core.database import db
from handlers.client_admin import admin_kb
from utils.states import UserBooking
from datetime import datetime
import random
import string

client_router = Router()

@client_router.message(CommandStart())
async def client_start_cmd(message: Message, bot: Bot, state: FSMContext):
    await state.clear() 
    
    business = await db.businesses.find_one({"bot_token": bot.token})
    if not business:
        return

    # Super Admin မှ ယာယီရပ်ဆိုင်းထားခြင်း ရှိ/မရှိ စစ်ဆေးခြင်း
    if business.get("status") == "suspended":
        await message.answer("🚫 **ဤ Bot အား Super Admin မှ ယာယီရပ်ဆိုင်း (Suspend) ထားပါသည်။**\n\nအသေးစိတ်သိရှိလိုပါက Platform Admin ထံ ဆက်သွယ်ပါ။")
        return

    owner_id = business.get("owner_id")
    sub_admins = business.get("sub_admins", [])
    
    user_id = message.from_user.id
    is_owner = (user_id == owner_id)
    is_sub_admin = (user_id in sub_admins)

    # (၁) လ သက်တမ်း ကုန်/မကုန် စစ်ဆေးခြင်း
    expires_at = business.get("expires_at")
    if expires_at and datetime.utcnow() > expires_at:
        # သက်တမ်းကုန်နေလျှင်
        if is_owner or is_sub_admin:
            await message.answer("⚠️ **လူကြီးမင်း၏ Bot အသုံးပြုခွင့် (၁) လ (Free Trial) သက်တမ်း ကုန်ဆုံးသွားပါပြီ။**\n\nဆက်လက်အသုံးပြုလိုပါက System Admin ထံ ဆက်သွယ်၍ သက်တမ်းတိုးပါ။")
        else:
            await message.answer("⚠️ **ဤ Bot သည် လက်ရှိတွင် ဝန်ဆောင်မှု ယာယီရပ်နားထားပါသည်။**")
        return 

    # ပိုင်ရှင် (သို့) Admin အကူ ဖြစ်နေလျှင် Admin Panel ကို ပြမည်
    if is_owner or is_sub_admin:
        text = "🛠 **လုပ်ငန်းရှင် / Admin Panel** မှ ကြိုဆိုပါတယ်။\n\nလိုအပ်သော လုပ်ဆောင်ချက်ကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။"
        await message.answer(text, reply_markup=admin_kb(is_owner=is_owner), parse_mode="Markdown")
        
    else:
        # လက်ရှိ User မှာ Active ဖြစ်နေသော ဝန်ဆောင်မှု ရှိ/မရှိ စစ်ဆေးခြင်း
        active_subs = await db.subscriptions.find({"bot_token": bot.token, "user_id": message.from_user.id, "status": "active"}).to_list(length=10)
        
        cursor = db.services.find({"bot_token": bot.token, "status": "active"})
        services = await cursor.to_list(length=100)
        
        # 💥 NEW: Database မှ Custom Welcome Message ကို ဆွဲထုတ်ခြင်း (မရှိပါက Default စာသားပြမည်)
        welcome_msg = business.get("welcome_msg", "🌟 **ကျွန်ုပ်တို့၏ VIP ဝန်ဆောင်မှုမှ ကြိုဆိုပါတယ်။** 🌟")
        text = f"{welcome_msg}\n\n"
        
        keyboard = []
        
        if services:
            text += "ဝယ်ယူလိုသော ဝန်ဆောင်မှုကို အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ-\n"
            for s in services:
                keyboard.append([InlineKeyboardButton(text=f"🔹 {s['name']} - {s['price']} ကျပ်", callback_data=f"buy_{s['_id']}")])
        else:
            text += "လောလောဆယ် ဝယ်ယူနိုင်သော ဝန်ဆောင်မှုများ မရှိသေးပါ။\n"
            
        if active_subs:
            keyboard.append([InlineKeyboardButton(text="🔑 Backup Key (အကောင့်ပျက်လျှင် ပြန်ယူရန်)", callback_data="get_backup_key")])
        else:
            keyboard.append([InlineKeyboardButton(text="🔄 အကောင့်ဟောင်း ပြန်ယူရန် (Recover)", callback_data="recover_account")])
            
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

# Customer က Service တစ်ခုခုကို ဝယ်ယူရန် နှိပ်လိုက်သောအခါ
@client_router.callback_query(F.data.startswith("buy_"))
async def buy_service_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    service_id_str = callback.data.split("_")[1]
    
    service = await db.services.find_one({"_id": ObjectId(service_id_str)})
    business = await db.businesses.find_one({"bot_token": bot.token})
    
    if not service or not business:
        await callback.answer("❌ ဝန်ဆောင်မှု ရှာမတွေ့ပါ။", show_alert=True)
        return
        
    payment_info = business.get("payment_info", "ငွေပေးချေမှုအချက်အလက် မရှိသေးပါ။ Admin ကို ဆက်သွယ်ပါ။")
    
    duration_val = service.get("duration", 0)
    duration_text = "Lifetime (တစ်သက်လုံး)" if duration_val == 0 else f"{duration_val} ရက်"
    service_note = service.get("note", "မရှိပါ") # 💥 Note အား ဆွဲထုတ်ခြင်း
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    text = (
        f"💳 <b>'{service['name']}' ကို ဝယ်ယူရန် ငွေလွှဲရမည့် အချက်အလက်</b>\n\n"
        f"{payment_info}\n\n"
        f"💵 <b>ကျသင့်ငွေ:</b> {service['price']} ကျပ်\n"
        f"⏳ <b>သက်တမ်း:</b> {duration_text}\n"
        f"📝 <b>အသေးစိတ် (Note):</b> {service_note}\n\n"
        "⚠️ <b>အရေးကြီးသည်:</b> ငွေလွှဲပြီးပါက ငွေလွှဲပြေစာ (Slip Screenshot) ကို ဤနေရာသို့ ဓာတ်ပုံ (Photo) အဖြစ် ပို့ပေးပါ။"
    )
    
    # 💥 parse_mode="HTML" ပြောင်းသည်
    await callback.message.answer(text, parse_mode="HTML")
    await state.set_state(UserBooking.waiting_for_slip)
    await state.update_data(buy_service_id=service_id_str)
    await callback.answer()
    
# Customer ဆီမှ Slip ပုံကို လက်ခံရရှိသောအခါ
@client_router.message(UserBooking.waiting_for_slip, F.photo)
async def receive_slip_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    service_id_str = data.get("buy_service_id")
    
    service = await db.services.find_one({"_id": ObjectId(service_id_str)})
    business = await db.businesses.find_one({"bot_token": bot.token})
    
    if not service or not business:
        await message.answer("❌ စနစ်ချို့ယွင်းမှု ရှိနေပါသည်။ ကျေးဇူးပြု၍ /start ကို ပြန်နှိပ်ပါ။")
        await state.clear()
        return
        
    # Database တွင် စောင့်ဆိုင်းဆဲစာရင်း (Pending Subscription) သွားမှတ်မည်
    sub_result = await db.subscriptions.insert_one({
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "bot_token": bot.token,
        "service_id": service_id_str,
        "status": "pending"
    })
    sub_id = str(sub_result.inserted_id)
    
    # ဝယ်ယူသူထံ စာပြန်မည်
    await message.answer("⏳ လူကြီးမင်း၏ ငွေလွှဲပြေစာကို လက်ခံရရှိပါပြီ။ Admin ၏ စစ်ဆေးအတည်ပြုချက်ကို ခေတ္တစောင့်ဆိုင်းပေးပါ။ အတည်ပြုပြီးပါက Group Link ကို အလိုအလျောက် ပေးပို့ပေးပါမည်။")
    await state.clear()
    
    # ทำการ ပိုင်ရှင် (Owner) ဆီသို့ Slip ပုံနှင့် Approve/Reject ခလုတ် လှမ်းပို့မည်
    owner_id = business.get("owner_id")
    photo_id = message.photo[-1].file_id # အကြည်ဆုံးပုံကို ယူမည်
    
    # 💥 ပြင်ဆင်ထားသော HTML ကုဒ်
    admin_text = (
        f"💰 <b>ငွေလွှဲပြေစာအသစ် ရောက်ရှိလာပါသည်!</b>\n\n"
        f"👤 <b>ဝယ်ယူသူ:</b> {message.from_user.full_name} (@{message.from_user.username})\n"
        f"📦 <b>Service:</b> {service['name']}\n"
        f"💵 <b>ဈေးနှုန်း:</b> {service['price']} ကျပ်\n"
    )
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"sub_approve_{sub_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"sub_reject_{sub_id}")
        ]
    ])
    
    try:
        # 💥 parse_mode="HTML" ပြောင်းသည်
        await bot.send_photo(chat_id=owner_id, photo=photo_id, caption=admin_text, reply_markup=admin_keyboard, parse_mode="HTML")
    except Exception as e:
        print(f"Failed to send slip to admin: {e}")

# ==========================================
# 💥 NEW: Request to Join တောင်းလာသူများကို စစ်ဆေးခြင်း
# ==========================================
@client_router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest, bot: Bot):
    user_id = update.from_user.id
    chat_id = str(update.chat.id) # ဝင်ခွင့်တောင်းသော Group ၏ ID

    # ထို User တွင် လက်ရှိ Bot ၌ Active ဖြစ်နေသော Subscription များရှိမရှိ ရှာမည်
    cursor = db.subscriptions.find({
        "user_id": user_id, 
        "bot_token": bot.token, 
        "status": "active"
    })
    subs = await cursor.to_list(length=100)

    is_allowed = False
    for sub in subs:
        # User ဝယ်ထားသော Service ထဲက Link(Chat ID) နှင့် ဝင်ခွင့်တောင်းသော Chat ID တူမတူ စစ်ဆေးမည်
        service = await db.services.find_one({"_id": ObjectId(sub["service_id"])})
        if service and service.get("link") == chat_id:
            is_allowed = True
            break

    # သေချာစွာ စစ်ဆေးပြီးနောက်
    if is_allowed:
        await update.approve() # မှန်ကန်သော ဝယ်ယူသူဖြစ်၍ အလိုအလျောက် လက်ခံပေးမည်
        try:
            await bot.send_message(user_id, "✅ Group/Channel သို့ ဝင်ခွင့်ပြုလိုက်ပါပြီ။")
        except:
            pass
    else:
        await update.decline() # မသက်ဆိုင်သူ ဖြစ်၍ အလိုအလျောက် ပယ်ချမည်
        try:
            await bot.send_message(user_id, "❌ သင့်တွင် ဝင်ခွင့် (Active Subscription) မရှိသောကြောင့် ဝင်ခွင့်ပယ်ချလိုက်ပါသည်။")
        except:
            pass

    # ==========================================
    # 💥 လင့်ခ်ကို အလိုအလျောက် ပိတ်ပစ်မည် (Auto-Revoke) 
    # ==========================================
    # User ဝင်ခွင့်တောင်းလိုက်သော လင့်ခ်အား အခြားသူများ ထပ်သုံးမရအောင် ချက်ချင်း ပိတ်ပစ်မည်
    if update.invite_link:
        try:
            await bot.revoke_chat_invite_link(chat_id=chat_id, invite_link=update.invite_link.invite_link)
        except Exception as e:
            print(f"Failed to revoke link: {e}")

# ==========================================
# 💥 NEW: Account Recovery (အကောင့်ဟောင်း ပြန်ယူခြင်း စနစ်)
# ==========================================
@client_router.callback_query(F.data == "get_backup_key")
async def get_backup_key(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    
    # Active ဖြစ်နေသော စာရင်းတစ်ခုကို ရှာမည်
    sub = await db.subscriptions.find_one({"bot_token": bot.token, "user_id": user_id, "status": "active"})
    if not sub:
        await callback.answer("Active ဝန်ဆောင်မှု မရှိပါ။", show_alert=True)
        return

    backup_key = sub.get("backup_key")
    # Key မရှိသေးပါက အသစ်ထုတ်ပေးမည် (ဥပမာ - BKP-A1B2C3)
    if not backup_key:
        random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        backup_key = f"BKP-{random_str}"
        
        # User ၏ Active ဖြစ်နေသော စာရင်းအားလုံးတွင် ဤ Key ကို မှတ်သားမည်
        await db.subscriptions.update_many(
            {"bot_token": bot.token, "user_id": user_id, "status": "active"},
            {"$set": {"backup_key": backup_key}}
        )

    text = (
        f"🔑 **သင့်၏ Backup Key မှာ:** `{backup_key}`\n\n"
        "⚠️ ဤ Key အား Copy ကူး၍ လုံခြုံသောနေရာတွင် သေချာစွာ မှတ်သားထားပါ။ သင့်အကောင့် ပျက်သွားပါက အကောင့်သစ်မှတစ်ဆင့် ဤ Key ကိုအသုံးပြု၍ သင်၏ ဝန်ဆောင်မှုများကို ပြန်လည်ရယူနိုင်ပါသည်။"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@client_router.callback_query(F.data == "recover_account")
async def ask_recover_key(callback: CallbackQuery, state: FSMContext):
    text = "🔄 **အကောင့်ဟောင်း ပြန်ယူခြင်း**\n\nလူကြီးမင်း၏ ယခင်အကောင့်မှ ရယူထားသော `Backup Key` (ဥပမာ BKP-XXXXXX) ကို ရိုက်ထည့်ပါ။"
    await callback.message.answer(text)
    await state.set_state(UserBooking.waiting_for_recovery_key)
    await callback.answer()


@client_router.message(UserBooking.waiting_for_recovery_key)
async def process_recovery_key(message: Message, state: FSMContext, bot: Bot):
    input_key = message.text.strip()
    
    # Database ထဲတွင် ထို Key ဖြင့် Active ဖြစ်နေသော စာရင်းများကို ရှာမည်
    cursor = db.subscriptions.find({"bot_token": bot.token, "backup_key": input_key, "status": "active"})
    subs = await cursor.to_list(length=100)

    if not subs:
        await message.answer("❌ Key မှားယွင်းနေပါသည် (သို့မဟုတ်) သက်တမ်းကုန်သွားသော Key ဖြစ်ပါသည်။\n\nပြန်လည်ကြိုးစားရန် /start ကို နှိပ်ပါ။")
        await state.clear()
        return

    # လုံခြုံရေးအရ Key အသစ်တစ်ခု ချက်ချင်းပြောင်းပေးမည် (တစ်ခြားသူ ပြန်ခိုးသုံး၍ မရစေရန်)
    new_random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    new_backup_key = f"BKP-{new_random_str}"
    
    keyboard = [] # 💥 NEW: Group ဝင်ရန် ခလုတ်များ စုဆောင်းရန်

    for sub in subs:
        old_user_id = sub["user_id"]
        service_id = sub["service_id"]

        service = await db.services.find_one({"_id": ObjectId(service_id)})
        if service:
            chat_id = service.get("link")
            if chat_id and (chat_id.startswith("-100") or chat_id.startswith("@")):
                # (၁) အကောင့်ဟောင်းအား အလိုအလျောက် ကန်ထုတ်ခြင်း
                try:
                    await bot.ban_chat_member(chat_id=chat_id, user_id=old_user_id)
                    await bot.unban_chat_member(chat_id=chat_id, user_id=old_user_id)
                except Exception as e:
                    print(f"Failed to kick old user {old_user_id}: {e}")
                
                # 💥 (၂) NEW: အကောင့်သစ်အတွက် ဝင်ခွင့် Link အသစ် ချက်ချင်း ထုတ်ပေးခြင်း
                try:
                    link_obj = await bot.create_chat_invite_link(
                        chat_id=chat_id, 
                        creates_join_request=True, 
                        name=f"Recovered ID: {message.from_user.id}"
                    )
                    keyboard.append([InlineKeyboardButton(text=f"🚀 Join {service['name']}", url=link_obj.invite_link)])
                except Exception as e:
                    print(f"Error creating recovery link: {e}")
            else:
                # Group ID မဟုတ်ဘဲ ရိုးရိုး Link အသေ ဖြစ်နေပါက
                if chat_id:
                    keyboard.append([InlineKeyboardButton(text=f"🚀 Join {service['name']}", url=chat_id)])

        # ထို့နောက် Database တွင် အကောင့်သစ်၏ အချက်အလက်များဖြင့် အစားထိုး Update လုပ်မည်
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "full_name": message.from_user.full_name,
                "backup_key": new_backup_key
            }}
        )

    success_text = (
        "✅ **အကောင့်ပြန်လည်ရယူခြင်း အောင်မြင်ပါသည်။**\n\n"
        "ယခင်အကောင့်ရှိ ဝန်ဆောင်မှုများကို ဤအကောင့်သစ်သို့ အောင်မြင်စွာ လွှဲပြောင်းပေးလိုက်ပါပြီ။ \n"
        "*(လုံခြုံရေးအရ သင်၏ ယခင်အကောင့်ဟောင်းအား Group များမှ အလိုအလျောက် ဖယ်ရှားလိုက်ပါပြီ)*\n\n"
        "👇 **အောက်ပါခလုတ်များကို နှိပ်၍ သက်ဆိုင်ရာ Group / Channel များသို့ ပြန်လည်ဝင်ရောက်နိုင်ပါပြီ။**"
    )
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    await message.answer(success_text, reply_markup=reply_markup, parse_mode="Markdown")
    await state.clear()
