from aiogram.fsm.state import State, StatesGroup

class AdminSetup(StatesGroup):
    waiting_for_payment_info = State()
    waiting_for_service_name = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    waiting_for_service_link = State()

class UserBooking(StatesGroup):
    waiting_for_slip = State()
    waiting_for_recovery_key = State() 

class AdminBroadcast(StatesGroup):
    waiting_for_msg = State()
class EditService(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_price = State()

    
