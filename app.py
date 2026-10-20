import json
from flask import Flask, make_response, jsonify, request
from datetime import datetime
import hashlib



app = Flask(__name__)



users = json.load(open("users.json", encoding="utf-8"))
lots = json.load(open("parking_lots.json", encoding="utf-8"))





#Mongo connection
#client = MongoClient("mongodb://localhost:27017")
#db = client.bizDB
#businesses = db.biz







# The welcome route
@app.route("/", methods=["GET"])
def index():
    return make_response("<h1>Smart Parking Management System API</h1>", 200)




# --------  For Guest user ---------------




# View all parking lots
@app.route("/api/v1.0/parking_lots", methods=['GET'])
def show_all_parking_lots():
    page_num, page_size = 1, 10

    if request.args.get("pn"):
        page_num = int(request.args.get("pn"))

    if request.args.get("ps"):
        page_size = int(request.args.get("ps"))

    page_start = page_size * (page_num - 1)

    data_to_return = []

    for lot in lots[page_start:page_start + page_size]:
        data_to_return.append({
            "parking_id": lot["parking_id"],
            "address": lot["address"],
            "location": lot["location"],
            "total_spaces": lot["total_spaces"],
            "num_available_spaces": lot["num_available_spaces"],
            "updated_at": lot["updated_at"],
            "price_per_hour": lot["price_per_hour"]
        })

    return make_response(jsonify(data_to_return), 200)


# View one parking lot
@app.route("/api/v1.0/parking_lots/<string:parking_id>", methods=['GET'])
def show_one_parking_lot(parking_id):
    for lot in lots:
        if str(lot["parking_id"]) == parking_id:
            return make_response(jsonify(lot), 200)

    return make_response(jsonify({"error": "Invalid parking lot ID"}), 404)







# Search car parks by location and time
@app.route("/api/v1.0/parking_lots/search", methods= ['GET'])
def search_parking():

    if not all(key in request.args for key in ["lat", "lng", "start", "end"]):
        return make_response(jsonify({"error": "Missing required parameters"}), 400)


    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
        radius = float(request.args.get("radius", 5))
        start = request.args["start"]
        end = request.args["end"]

        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))

    except ValueError:
        return make_response(jsonify({"error": "Invalid search parameters"}), 400)

    # Check the time period
    if end_time <= start_time:
        return make_response(jsonify({"error": "End time must be after start time"}), 400)

    hours = (end_time - start_time).total_seconds() / 3600

    results = []

    #Check each parking lot
    for lot in lots:

        # Count reservations that overlap the requested time
        taken = 0

        for reservation in lot.get("reservations", []):
            reservation_start = datetime.fromisoformat(
                reservation["start_time"].replace("Z", "+00:00")
            )
            reservation_end = datetime.fromisoformat(
                reservation["end_time"].replace("Z", "+00:00")
            )

            if (
                reservation["status"] not in ["cancelled", "rejected"]
                and reservation_start < end_time
                and start_time < reservation_end
            ):
                taken += 1

        # Calculate available spaces
        free_spaces = lot["total_spaces"] - taken

        # Calculate approximate distance in kilometres
        lot_lng, lot_lat = lot["location"]["coordinates"]

        distance = (
            ((lat - lot_lat) * 111) ** 2
            + ((lng - lot_lng) * 69) ** 2
        ) ** 0.5

        # Add the car park if it is nearby and has space
        if free_spaces > 0 and distance <= radius:
            results.append({
                "parking_id": lot["parking_id"],
                "address": lot["address"],
                "distance_km": round(distance, 2),
                "free_spaces": free_spaces,
                "price_per_hour": lot["price_per_hour"],
                "total_price": round(hours * lot["price_per_hour"], 2)
            })

    # Show nearest car parks first
    results.sort(key=lambda lot: lot["distance_km"])

    return make_response(jsonify(results), 200)








# --------  Register and Login, And endpoints for Logged in user ---------------


# Create a user
@app.route("/api/v1.0/auth/register", methods = ['POST'])
def register():

    if not all(key in request.values for key in ["name", "email", "password"]):
        return make_response(jsonify({"error": "Missing required fields"}), 400)

    name = request.values["name"]
    email = request.values["email"]
    password = request.values["password"]

    # Check if email already exists
    for user in users:
        if user["user_id"] == email:
            return make_response(jsonify({"error": "This email is already registered"}), 409)


    new_user = {
        "role": "user",
        "user_id": email,
        "name": name,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        "reservation_details": []
    }


    users.append(new_user)

    return make_response(jsonify({
        "message": "User registered",
        "user_id": email
    }), 201)




 

# login
@app.route("/api/v1.0/auth/login", methods= ['POST'])
def login():

    # Check required fields
    if not all(key in request.values for key in ["email", "password"]):
        return jsonify({"error": "Missing required fields"}), 400

    email = request.values["email"]
    password = request.values["password"]

    user = None
    for u in users:
        if u["user_id"] == email:
            user = u
            break


    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if user is None or user["password_hash"] != password_hash:
        return make_response(jsonify({"error": "Wrong email or password"}), 401)


    return make_response(jsonify({
        "message": "Login successful",
        "token": "dummy-token",
        "user_id": user["user_id"],
        "role": user["role"]
    }), 200)





#Each logged in user can view their own account. 
@app.route("/api/auth/me", methods=["GET"])
def me():

    user_id = request.args.get("user_id")

    # Find the user
    user = None
    for u in users:
        if u["user_id"] == user_id:
            user = u
            break


    if user is None:
        return make_response(jsonify({"error": "Send a valid user_id"}), 401)


    account = {
        "user_id": user["user_id"],
        "name": user["name"],
        "role": user["role"]
    }

    # Include managed parking lots for administrators
    if user["role"] == "admin":
        account["managed_parking_lots"] = [
            lot["parking_id"] for lot in user["managed_parking_lots"]
        ]

    return make_response(jsonify(account), 200)







# POST /api/reservations: submit a reservation request. 
# GET /api/reservations: view own reservations. 
# GET /api/reservations/<id>: view a specific reservation. 
# PUT /api/reservations/<id>: update an eligible reservation. 
# PUT /api/reservations/<id>/cancel: cancel a reservation. 
# POST /api/sessions/<id>/check-in: check in using an approved reservation. 
# POST /api/sessions/<id>/check-out: check out and complete the parking session. 
# GET /api/sessions/history: view previous parking sessions. 
# GET /api/recommendations: recommend suitable car parks based on factors such as 
#distance, price, and availability. 







if __name__== "__main__":
    app.run(debug=True, port=5001)