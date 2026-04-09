from pymongo import MongoClient
import redis

mongo_client = MongoClient("mongodb://localhost:27017")
db = mongo_client["healthcare_chatbot"]
messages_collection = db["messages"]

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
