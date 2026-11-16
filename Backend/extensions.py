from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.ParkingDB
users = db.users
parking_lots = db.parking_lots
blacklist = db.blacklist

# "$near" in /me/recommendations only works with a 2dsphere index
parking_lots.create_index([("location", "2dsphere")])