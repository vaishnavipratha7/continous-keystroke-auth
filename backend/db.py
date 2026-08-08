import pymongo
from bson import ObjectId

# Initialize MongoDB client
MONGO_URI = "mongodb://localhost:27017/"
client = pymongo.MongoClient(MONGO_URI)
db = client["keystroke_auth_db"]

# Collections
users_col = db["users"]
keystroke_events_col = db["keystroke_events"]
user_models_col = db["user_models"]
session_scores_col = db["session_scores"]

def get_user_by_username(username):
    return users_col.find_one({"username": username})

def get_user_by_id(user_id):
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    return users_col.find_one({"_id": user_id})
