import os
from motor.motor_asyncio import AsyncIOMotorClient


def get_db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]
