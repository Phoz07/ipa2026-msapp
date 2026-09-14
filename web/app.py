import ipaddress
import os
from urllib.parse import quote_plus

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = Flask(__name__)

mongo_username = os.environ.get("MONGO_INITDB_ROOT_USERNAME")
mongo_password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD")
mongo_host = os.environ.get("MONGO_HOST", "mongo")
mongo_port = os.environ.get("MONGO_PORT", "27017")

if mongo_username and mongo_password:
    default_mongo_uri = (
        f"mongodb://{quote_plus(mongo_username)}:{quote_plus(mongo_password)}"
        f"@{mongo_host}:{mongo_port}/?authSource=admin"
    )
else:
    default_mongo_uri = f"mongodb://{mongo_host}:{mongo_port}/"

client = MongoClient(
    os.environ.get("MONGO_URI", default_mongo_uri),
    serverSelectionTimeoutMS=5000,
)
database = client[os.environ.get("MONGO_DB", "mydatabase")]
routers = database[os.environ.get("MONGO_COLLECTION", "mycollection")]


def normalize_ip_address(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (AttributeError, ValueError):
        return None


@app.route("/")
def main():
    try:
        data = list(routers.find().sort("ip_address", 1))
        error = None
    except PyMongoError:
        app.logger.exception("Cannot load routers from MongoDB")
        data = []
        error = "Cannot connect to MongoDB."

    return render_template("index.html", data=data, error=error)


@app.route("/add", methods=["POST"])
def add_router():
    ip_address = normalize_ip_address(request.form.get("ip_address", ""))
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if ip_address and username and password:
        try:
            routers.update_one(
                {"ip_address": ip_address},
                {
                    "$set": {
                        "username": username,
                        "password": password,
                    }
                },
                upsert=True,
            )
        except PyMongoError:
            app.logger.exception("Cannot save router to MongoDB")

    return redirect(url_for("main"))


@app.route("/delete", methods=["POST"])
def delete_router():
    router_id = request.form.get("router_id", "")

    try:
        routers.delete_one({"_id": ObjectId(router_id)})
    except (InvalidId, PyMongoError):
        app.logger.exception("Cannot delete router")

    return redirect(url_for("main"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
