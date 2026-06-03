from aiogram.fsm.state import State, StatesGroup

class AdminSetup(StatesGroup):
    waiting_for_payment_info = State()
    
    # အောက်ပါ State များကို Service အသစ်ထည့်ရန် ပေါင်းထည့်ထားပါသည်
    waiting_for_service_name = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    waiting_for_service_link = State()
