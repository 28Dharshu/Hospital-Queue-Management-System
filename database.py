from pymongo import MongoClient
import os

# Connecting to local MongoDB by default
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)

db = client["hospital_ai"]

# Collections

users_collection = db["users"]
queue_collection = db["queue"]
