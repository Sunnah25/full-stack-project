from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, current_app, request

from auth_utils import login_required
from extensions import users
from helpers import error, hash_password, managed_ids, reply

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1.0/auth")


# 4. Register
@auth_bp.route("/register", methods=["POST"])
def register():
    name, email, password = (request.values.get(k) for k in ["name", "email", "password"])

    if not (name and email and password):
        return error("Missing from data", 400)

    if "@" not in email or len(password) < 6:
        return error("Invalid email, or password shorter than 6 characters", 400)

    if users.find_one({"user_id": email}) is not None:
        return error("This email is already registered", 409)

    users.insert_one({
        "role": "user",
        "user_id": email,
        "name": name,
        "password_hash": hash_password(password),
        "reservation_details": []})

    return reply({"message": "User registered", "user_id": email}, 201)


# 5. Login
@auth_bp.route("/login", methods=["POST"])
def login():
    email, password = request.values.get("email"), request.values.get("password")

    if not (email and password):
        return error("Missing required fields", 400)

    user = users.find_one({"user_id": email})

    if user is None or user["password_hash"] != hash_password(password):
        return error("Wrong email or password", 401)

    token = jwt.encode(
        {"user_id": user["user_id"],
         "role": user["role"],
         "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        current_app.config["SECRET_KEY"], algorithm="HS256")

    return reply({"message": "Login successful", "token": token,
                  "user_id": user["user_id"], "role": user["role"]})


# 6. View own data
@auth_bp.route("/me", methods=["GET"])
@login_required()
def me(user):
    account = {"user_id": user["user_id"], "name": user["name"], "role": user["role"]}

    if user["role"] == "admin":
        account["managed_parking_lots"] = managed_ids(user)

    return reply(account)