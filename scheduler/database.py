import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def get_mongo_uri():
    configured_uri = os.environ.get("MONGO_URI")
    if configured_uri:
        return configured_uri

    username = os.environ.get("MONGO_INITDB_ROOT_USERNAME")
    password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD")
    host = os.environ.get("MONGO_HOST", "mongo")
    port = os.environ.get("MONGO_PORT", "27017")

    if username and password:
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/?authSource=admin"
        )

    return f"mongodb://{host}:{port}/"


def get_router_info():
    db_name = os.environ.get("MONGO_DB", "mydatabase")
    collection_name = os.environ.get("MONGO_COLLECTION", "mycollection")

    with MongoClient(get_mongo_uri(), serverSelectionTimeoutMS=5000) as client:
        routers = client[db_name][collection_name]
        return list(routers.find())


if __name__ == "__main__":
    for router in get_router_info():
        print(router)
