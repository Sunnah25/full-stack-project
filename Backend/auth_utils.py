from functools import wraps

import jwt
from flask import current_app, request

from extensions import blacklist, users
from helpers import error


# Check the token, make sure it was not logged out, load the user, check the role.
def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            token = request.headers.get("x-access-token")

            if not token:
                return error("Token required", 401)


            try:
                data = jwt.decode(token,
                                  current_app.config["SECRET_KEY"],
                                  algorithms=["HS256"])

            except jwt.ExpiredSignatureError:
                return error("Token expired", 401)

            except jwt.InvalidTokenError:
                return error("Invalid token", 401)

            if blacklist.find_one({"token": token}) is not None:
                return error("Token has been logged out", 401)

            user = users.find_one({"user_id": data.get("user_id")})

            if user is None:
                return error("User not found", 404)

            if role and user["role"] != role:
                return error(role.capitalize() + " access only", 403)

            return view(user, *args, **kwargs)

        return wrapper

    return decorator