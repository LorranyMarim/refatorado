from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def get_mongo_db():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
    client = MongoClient(mongo_url)
    return client["senai_betim_bd"]