from info import AUTH_CHANNEL, OTHER_DB_URI
from database.db_helpers import get_async_mongo_client
import motor.motor_asyncio

class JoinReqs:

    def __init__(self):
        self.collection = "join_requests"
        if OTHER_DB_URI:
            self.client = get_async_mongo_client(OTHER_DB_URI)
            self.db = self.client["RequestDb"]
            self.dcol = self.db[self.collection]
        else:
            self.client = None
            self.db = None
            self.dcol = None

    def isActive(self):
        if self.client is not None:
            return True
        else:
            return False

    async def add_user(self, user_id, first_name, username, date):
        try:
            await self.dcol.insert_one({"_id": int(user_id),"user_id": int(user_id), "first_name": first_name, "username": username, "date": date})
        except:
            pass

    async def get_user(self, user_id):
        return await self.dcol.find_one({"user_id": int(user_id)})

    async def get_all_users(self):
        return await self.dcol.find().to_list(None)

    async def delete_user(self, user_id):
        await self.dcol.delete_one({"user_id": int(user_id)})

    async def delete_all_users(self):
        await self.dcol.delete_many({})

    async def get_all_users_count(self):
        return await self.dcol.count_documents({})
