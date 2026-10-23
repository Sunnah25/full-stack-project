from functools import wraps

import jwt
from flask import current_app, request

from extensions import users
from helpers import error


# Check the JWT, load the user, check the role.
def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")

            if not auth.startswith("Bearer "):
                return error("Token required", 401)

            try:
                data = jwt.decode(auth.split(" ", 1)[1],
                                  current_app.config["SECRET_KEY"],
                                  algorithms=["HS256"])

            except jwt.ExpiredSignatureError:
                return error("Token expired", 401)

            except jwt.InvalidTokenError:
                return error("Invalid token", 401)

            user = users.find_one({"user_id": data.get("user_id")})

            if user is None:
                return error("User not found", 404)

            if role and user["role"] != role:
                return error(role.capitalize() + " access only", 403)

            return view(user, *args, **kwargs)

        return wrapper

    return decorator