from bson import ObjectId
from pymongo import MongoClient

# เชื่อมต่อ MongoDB
client = MongoClient("mongodb://localhost:27017/")
mydb = client["mydatabase"]
mycol = mydb["mycollection"]

print("--- Initial Databases & Collections ---")
print("Databases:", client.list_database_names())
print("Collections:", mydb.list_collection_names())

print("\n--- 1. Insert Documents ---")
john = mycol.insert_one({"name": "John", "address": "Highway 37"})
print("Inserted John:", john.inserted_id)

mycol.insert_one({"name": "Alice", "address": "Highway 27"})
mycol.insert_one({"name": "Bob", "address": "Highway 17"})
mycol.insert_one({"name": "Carl", "address": "Highway 27"})
dave = mycol.insert_one({"name": "Dave", "address": "Highway 7"})
print("Inserted Dave:", dave.inserted_id)

print("\n--- 2. Find One ---")
print(mycol.find_one())

print("\n--- 3. Find All ---")
for doc in mycol.find():
    print(doc)

print("\n--- 4. Query & Sort (address: Highway 27, sort by name DESC) ---")
for doc in mycol.find({"address": "Highway 27"}).sort("name", -1):
    print(doc)

print("\n--- 5. Delete One (address: Highway 27) ---")
res = mycol.delete_one({"address": "Highway 27"})
print(f"{res.deleted_count} documents deleted.")

print("\n--- 6. Insert Alice again ---")
mycol.insert_one({"name": "Alice", "address": "Highway 27"})

print("\n--- 7. Delete Many (address: Highway 27) ---")
res = mycol.delete_many({"address": "Highway 27"})
print(f"{res.deleted_count} documents deleted.")

print("\n--- 8. Delete by ObjectId (John's ID) ---")
# ใช้ ObjectId จริงที่เพิ่งสร้างในรอบนี้เพื่อทดสอบการลบผ่าน bson.ObjectId
res = mycol.delete_one({"_id": ObjectId(john.inserted_id)})
print(f"{res.deleted_count} documents deleted.")

print("\n--- 9. Remaining Documents ---")
for doc in mycol.find():
    print(doc)

print("\n--- 10. Clean Up All Documents ---")
res = mycol.delete_many({})
print(f"{res.deleted_count} documents deleted.")

print("\n--- Final Check ---")
print("Databases:", client.list_database_names())
print("Collections:", mydb.list_collection_names())

client.close()
print("\nTest completed successfully.")
