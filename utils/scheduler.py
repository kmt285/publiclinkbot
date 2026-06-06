import logging
from datetime import datetime, timedelta
from aiogram import Bot
from bson.objectid import ObjectId
from core.database import db

async def check_expired_subscriptions():
    logging.info("🔍 Checking for expired subscriptions...")
    now = datetime.utcnow()
    
    # DB ထဲတွင် Active ဖြစ်နေပြီး၊ သက်တမ်းကုန်ဆုံးရက်သည် ယခုအချိန်ထက် စောနေသော စာရင်းများကို ရှာမည်
    cursor = db.subscriptions.find({
        "status": "active",
        "end_date": {"$ne": None, "$lt": now}
    })
    expired_subs = await cursor.to_list(length=100)
    
    for sub in expired_subs:
        user_id = sub["user_id"]
        bot_token = sub["bot_token"]
        service_id = sub["service_id"]
        
        service = await db.services.find_one({"_id": ObjectId(service_id)})
        if not service:
            continue
            
        chat_id = service.get("link")
        
        # လုံခြုံသော Group ID (-100...) ဖြစ်မှသာ ထုတ်ပစ်မည်
        if chat_id and (chat_id.startswith("-100") or chat_id.startswith("@")):
            try:
                bot = Bot(token=bot_token)
                
                # User ကို Group ထဲမှ Kick လုပ်မည် (Ban ပြီး ချက်ချင်း Unban လုပ်ခြင်းဖြင့် ဖယ်ရှားသည်)
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
                
                # User ထံသို့ အသိပေး Message ပို့မည်
                msg = (
                    f"⚠️ **သက်တမ်းကုန်ဆုံးခြင်း အသိပေးချက်**\n\n"
                    f"လူကြီးမင်း ဝယ်ယူထားသော **{service['name']}** ၏ သက်တမ်းမှာ ကုန်ဆုံးသွားပြီဖြစ်သောကြောင့် Group ထဲမှ အလိုအလျောက် ဖယ်ရှားလိုက်ပါသည်။\n\n"
                    f"ဆက်လက်အသုံးပြုလိုပါက ဤ Bot ထဲတွင် /start ကိုနှိပ်၍ သက်တမ်းပြန်လည် တိုးနိုင်ပါသည်။"
                )
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
                
                # Bot Session ကို ပိတ်မည် (Memory မပြည့်စေရန်)
                await bot.session.close()
            except Exception as e:
                logging.error(f"Failed to kick user {user_id} from {chat_id}: {e}")
        
        # Database တွင် status ကို 'expired' ဟု ပြောင်းလဲ မှတ်သားမည်
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": "expired"}}
        )
    
    logging.info(f"✅ Auto-kick process completed. {len(expired_subs)} users expired.")

async def check_business_expirations(master_bot):
    now = datetime.utcnow()
    businesses = await db.businesses.find({"expires_at": {"$ne": None}}).to_list(length=1000)
    
    for biz in businesses:
        exp = biz.get("expires_at")
        if not exp: continue
        
        owner_id = biz.get("owner_id")
        time_left = exp - now
        days_left = time_left.days
        
        # ၁။ ၇-ရက် အလို သတိပေးခြင်း
        if days_left == 7 and not biz.get("notified_7"):
            try:
                await master_bot.send_message(owner_id, "⚠️ **သတိပေးချက်:** လူကြီးမင်း၏ Bot သက်တမ်း (၇) ရက်အတွင်း ကုန်ဆုံးပါတော့မည်။ ဆက်လက်အသုံးပြုရန် Master Bot တွင် ငွေပေးချေမှုပြုလုပ်ပါ။", parse_mode="Markdown")
                await db.businesses.update_one({"_id": biz["_id"]}, {"$set": {"notified_7": True}})
            except: pass
            
        # ၂။ ၃-ရက် အလို သတိပေးခြင်း
        elif days_left == 3 and not biz.get("notified_3"):
            try:
                await master_bot.send_message(owner_id, "⚠️ **အရေးကြီးသတိပေးချက်:** လူကြီးမင်း၏ Bot သက်တမ်း (၃) ရက်အတွင်း ကုန်ဆုံးပါတော့မည်။ သက်တမ်းမတိုးပါက စနစ်မှ ယာယီရပ်ဆိုင်းသွားမည်ဖြစ်သည်။", parse_mode="Markdown")
                await db.businesses.update_one({"_id": biz["_id"]}, {"$set": {"notified_3": True}})
            except: pass
            
        # ၃။ ၁-ရက် အလို သတိပေးခြင်း
        elif days_left == 1 and not biz.get("notified_1"):
            try:
                await master_bot.send_message(owner_id, "🚨 **နောက်ဆုံးသတိပေးချက်:** မနက်ဖြန်တွင် လူကြီးမင်း၏ Bot သက်တမ်းကုန်ဆုံးမည်ဖြစ်၍ ဝန်ဆောင်မှုများ အလိုအလျောက် ရပ်တန့်သွားပါမည်။", parse_mode="Markdown")
                await db.businesses.update_one({"_id": biz["_id"]}, {"$set": {"notified_1": True}})
            except: pass
            
        # ၄။ သက်တမ်းကုန်သွားပါက ချက်ချင်း SUSPEND လုပ်ခြင်း
        elif time_left.total_seconds() <= 0 and biz.get("status") == "active":
            await db.businesses.update_one({"_id": biz["_id"]}, {"$set": {"status": "suspended"}})
            try:
                await master_bot.send_message(owner_id, "🚫 **လူကြီးမင်း၏ Bot မှာ သက်တမ်းကုန်ဆုံးသွားသောကြောင့် ယာယီရပ်ဆိုင်း (Suspend) လိုက်ပါသည်။**\n\n(၇) ရက်အတွင်း သက်တမ်းမတိုးပါက Database အတွင်းမှ Data များအားလုံး အပြီးတိုင် ပျက်ပြယ်သွားမည် ဖြစ်ပါသည်။", parse_mode="Markdown")
            except: pass
            
        # ၅။ Suspend ဖြစ်ပြီး (၇) ရက် ကျော်လွန်သွားပါက DATABASE မှ အပြီးတိုင် ရှင်းထုတ်ခြင်း 💥
        elif time_left.total_seconds() <= - (7 * 24 * 3600):
            token = biz["bot_token"]
            await db.businesses.delete_one({"_id": biz["_id"]})
            await db.services.delete_many({"bot_token": token})
            await db.subscriptions.delete_many({"bot_token": token})
            try:
                await master_bot.send_message(owner_id, "🗑 **လူကြီးမင်း၏ Bot အား သက်တမ်းလွန်သွားသဖြင့် စနစ်မှ အပြီးတိုင် ရှင်းလင်းဖယ်ရှားလိုက်ပါပြီ။**\n\nကျေးဇူးပြု၍ စနစ်ကို ပြန်လည်အသုံးပြုလိုပါက Bot အသစ် ပြန်လည်ချိတ်ဆက်ပါ။", parse_mode="Markdown")
            except: pass
