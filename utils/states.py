from aiogram.fsm.state import State, StatesGroup

class AdminSetup(StatesGroup):
    waiting_for_welcome_msg = State()
    waiting_for_payment_info = State()
    waiting_for_service_name = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    waiting_for_service_note = State() 
    waiting_for_service_link = State()
    waiting_for_sub_admin_id = State() 
    waiting_for_remove_admin_id = State()

class UserBooking(StatesGroup):
    waiting_for_slip = State()
    waiting_for_recovery_key = State() 

class AdminBroadcast(StatesGroup):
    waiting_for_msg = State()
    
class EditService(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_price = State()
    waiting_for_new_note = State()
    waiting_for_new_channel = State()

class MasterSetup(StatesGroup):
    waiting_for_bot_token = State()

class MasterBooking(StatesGroup):
    waiting_for_slip = State()
    plan_days = State()

class MasterBroadcast(StatesGroup):
    waiting_for_msg = State()

    
