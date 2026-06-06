from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGODB_URI, DB_NAME

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        
        self.businesses = self.db.businesses
        self.services = self.db.services
        self.subscriptions = self.db.subscriptions
        self.users = self.db.users
        self.system_config = self.db.system_config

db = Database()
