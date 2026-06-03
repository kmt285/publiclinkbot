import logging
from datetime import datetime
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
