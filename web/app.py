import ipaddress
import os
from urllib.parse import quote_plus

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, url_for
from pymongo import DESCENDING, MongoClient
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
interface_results = database[
    os.environ.get("MONGO_RESULTS_COLLECTION", "router_interface_results")
]


def normalize_ip_address(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (AttributeError, ValueError):
        return None


def get_latest_interface_result(router):
    return interface_results.find_one(
        {
            "$or": [
                {"router_id": router["_id"]},
                {"ip_address": router["ip_address"]},
            ]
        },
        sort=[("timestamp", DESCENDING)],
    )


@app.route("/")
def main():
    try:
        data = list(routers.find().sort("ip_address", 1))
        for router in data:
            latest_result = get_latest_interface_result(router)
            interfaces = latest_result.get("result", []) if latest_result else []
            interfaces = interfaces if isinstance(interfaces, list) else []

            router["latest_result"] = latest_result
            router["interfaces_total"] = len(interfaces)
            router["interfaces_up"] = sum(
                interface.get("status", "").lower() == "up"
                for interface in interfaces
            )
        error = None
    except PyMongoError:
        app.logger.exception("Cannot load routers from MongoDB")
        data = []
        error = "Cannot connect to MongoDB."

    return render_template("index.html", data=data, error=error)


@app.route("/router/<ip_address>")
def router_detail(ip_address):
    normalized_ip = normalize_ip_address(ip_address)
    if normalized_ip is None:
        abort(404)

    try:
        router = routers.find_one({"ip_address": normalized_ip})
        if router is None:
            abort(404)

        history_limit = int(os.environ.get("INTERFACE_HISTORY_LIMIT", "10"))
        interface_history = list(
            interface_results.find(
                {
                    "$or": [
                        {"router_id": router["_id"]},
                        {"ip_address": router["ip_address"]},
                    ]
                }
            )
            .sort("timestamp", DESCENDING)
            .limit(history_limit)
        )
    except (PyMongoError, ValueError):
        app.logger.exception("Cannot load router interface status from MongoDB")
        abort(503)

    return render_template(
        "router_detail.html",
        router=router,
        interface_history=interface_history,
    )


@app.route("/routers/<router_id>")
def router_detail_by_id(router_id):
    try:
        router = routers.find_one({"_id": ObjectId(router_id)})
    except (InvalidId, PyMongoError):
        abort(404)

    if router is None:
        abort(404)

    return redirect(url_for("router_detail", ip_address=router["ip_address"]))


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
