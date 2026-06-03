from aiogram.fsm.state import State, StatesGroup

class AdminSetup(StatesGroup):
    waiting_for_payment_info = State()
    waiting_for_service_name = State()
