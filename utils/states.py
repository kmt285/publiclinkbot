from aiogram.fsm.state import State, StatesGroup

class AdminSetup(StatesGroup):
    waiting_for_payment_info = State()
    waiting_for_service_name = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    waiting_for_service_link = State()

class UserBooking(StatesGroup):
    waiting_for_slip = State()

class AdminBroadcast(StatesGroup):
    waiting_for_msg = State()ေ
