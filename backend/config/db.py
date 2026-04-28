from pymongo import MongoClient
import redis
import os

mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
db = mongo_client["healthcare_chatbot"]
messages_collection = db["messages"]
users_collection = db["users"]

redis_url = os.getenv("REDIS_URL", None)
if redis_url:
    redis_client = redis.from_url(redis_url, decode_responses=True)
else:
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
