import hashlib
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from math import cos, radians

import jwt
from flask import Flask, jsonify, make_response, request
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

# database 
client = MongoClient("mongodb://localhost:27017")
db = client.ParkingDB
users = db.users
parking_lots = db.parking_lots

# "$near" in /recommendations only works with a 2dsphere index
parking_lots.create_index([("location", "2dsphere")])

API = "/api/v1.0"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FREE_STATUSES = ["cancelled", "rejected"]
ALL_STATUSES = ["pending", "approved", "rejected", "active", "completed", "cancelled"]
LOT_FIELDS = ["street", "city", "postcode", "latitude", "longitude",
              "total_spaces", "price_per_hour"]
LOT_SUMMARY = ["parking_id", "address", "location", "total_spaces",
               "num_available_spaces", "updated_at", "price_per_hour"]


# helper functions
def error(message, code):
    return make_response(jsonify({"error": message}), code)


def reply(body, code=200):
    return make_response(jsonify(body), code)


def now_str():
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def parse_time(text):
    #ISO string = timezone aware datetime (raises ValueError if invalid)
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("timezone missing")
    return value


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def find_item(items, key, value):
    #First dict in a list where item[key] == value, else None.
    return next((item for item in items if item[key] == value), None)


def get_paging():
    page = int(request.args.get("pn", 1))
    size = int(request.args.get("ps", 10))
    if page < 1 or size < 1:
        raise ValueError("bad paging")
    return page, size


def distance_km(lat1, lng1, lat2, lng2):
    dy = (lat2 - lat1) * 111
    dx = (lng2 - lng1) * 111 * cos(radians(lat1))
    return (dx ** 2 + dy ** 2) ** 0.5


def read_location():
    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
        radius = float(request.args.get("radius", 5))
    except (KeyError, ValueError):
        return None, None, None, error("lat, lng and radius must be numbers", 400)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180) or radius <= 0:
        return None, None, None, error("Invalid location or radius", 400)
    return lat, lng, radius, None


def next_id(prefix, width, existing_ids):
    highest = max((int(i[1:]) for i in existing_ids), default=0)
    return prefix + str(highest + 1).zfill(width)


def all_reservations():
    for lot in parking_lots.find({}, {"reservations": 1}):
        yield from lot.get("reservations", [])


def count_taken(lot, start, end, ignore_id=None):
    taken = 0
    for r in lot.get("reservations", []):
        if r["reservation_id"] == ignore_id or r["status"] in FREE_STATUSES:
            continue
        if parse_time(r["start_time"]) < end and start < parse_time(r["end_time"]):
            taken += 1
    return taken


def vehicles_inside(lot):
    return lot["availability_history"][-1]["vehicles_inside"]


def managed_ids(admin):
    return [m["parking_id"] for m in admin.get("managed_parking_lots", [])]


def save_availability(parking_id, total_spaces, inside, now, extra=None):
    free = total_spaces - len(inside)
    fields = {"num_available_spaces": free, "updated_at": now, **(extra or {})}
    parking_lots.update_one(
        {"parking_id": parking_id},
        {"$set": fields,
         "$push": {"availability_history": {
             "updated_at": now,
             "num_available_spaces": free,
             "vehicles_inside": inside}}})


def update_everywhere(reservation_id, user_id, parking_id, changes):
    def build(prefix):
        return {prefix + key: value for key, value in changes.items()}

    # 1 user data
    users.update_one(
        {"user_id": user_id, "reservation_details.reservation_id": reservation_id},
        {"$set": build("reservation_details.$.")})
    
    # 2 parking lot data
    parking_lots.update_one(
        {"parking_id": parking_id, "reservations.reservation_id": reservation_id},
        {"$set": build("reservations.$.")})
    
    # 3 admin's data
    users.update_many(
        {"role": "admin", "managed_parking_lots.parking_id": parking_id},
        {"$set": build("managed_parking_lots.$[m].reservation_refs.$[r].")},
        array_filters=[{"m.parking_id": parking_id}, {"r.reservation_id": reservation_id}])











# -------------------------- auth ------------------------------------------



#Check the JWT, load the user, check the role.

def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            
            if not auth.startswith("Bearer "):
                return error("Token required", 401)
            
            try:
                data = jwt.decode(auth.split(" ", 1)[1],
                                  app.config["SECRET_KEY"], algorithms=["HS256"])
                
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






# ---------------------------- welcome route --------------------------------
@app.route("/", methods = ['GET'])
def index():
    return make_response("<h1>Smart Parking Management System API</h1>", 200)


# --------------------------- guest routes ----------------------------------

#1. View parking lots
@app.route(API + "/parking_lots", methods = ['GET'])
def show_all_parking_lots():
    try:
        page, size = get_paging()
    except ValueError:
        return error("pn and ps must be positive numbers", 400)

    lots = parking_lots.find().sort("parking_id", 1).skip((page - 1) * size).limit(size)
    return reply([{field: lot[field] for field in LOT_SUMMARY} for lot in lots])


# 2. View one specific parking lot
@app.route(API + "/parking_lots/<parking_id>", methods = ['GET'])
def show_one_parking_lot(parking_id):
    
    # hide private data (other drivers' reservations, income, vehicle numbers)
    lot = parking_lots.find_one(
        {"parking_id": parking_id},
        {"_id": 0, "reservations": 0, "income": 0, "availability_history": 0})
    
    if lot is None:
        return error("Invalid parking lot ID", 404)
    return reply(lot)



# 3. Search parking lot
# Example: /parking_lots/search?lat=51.51&lng=-0.13&start=2026-11-01T09:00:00Z&end=2026-11-01T12:00:00Z
@app.route(API + "/parking_lots/search", methods = ['GET'])
def search_parking():
    if not all(key in request.args for key in ["lat", "lng", "start", "end"]):
        return error("Missing required parameters", 400)

    lat, lng, radius, problem = read_location()
    if problem:
        return problem
    try:
        start, end = parse_time(request.args["start"]), parse_time(request.args["end"])
    except ValueError:
        return error("Invalid search parameters", 400)
    if end <= start:
        return error("End time must be after start time", 400)

    hours = (end - start).total_seconds() / 3600
    results = []
    for lot in parking_lots.find():
        free_spaces = lot["total_spaces"] - count_taken(lot, start, end)
        lot_lng, lot_lat = lot["location"]["coordinates"]
        distance = distance_km(lat, lng, lot_lat, lot_lng)

        if free_spaces > 0 and distance <= radius:
            results.append({
                "parking_id": lot["parking_id"],
                "address": lot["address"],
                "distance_km": round(distance, 2),
                "free_spaces": free_spaces,
                "price_per_hour": lot["price_per_hour"],
                "total_price": round(hours * lot["price_per_hour"], 2)})

    results.sort(key=lambda item: item["distance_km"])
    return reply(results)




# ------------------------- register / login --------------------------------

# 4. Register
@app.route(API + "/auth/register", methods=["POST"])
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
@app.route(API + "/auth/login", methods=["POST"])
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
        app.config["SECRET_KEY"], algorithm="HS256")
    
    return reply({"message": "Login successful", "token": token,
                  "user_id": user["user_id"], "role": user["role"]})


# 6. view own data
@app.route(API + "/auth/me", methods = ['GET'])
@login_required()
def me(user):
    account = {"user_id": user["user_id"], "name": user["name"], "role": user["role"]}
    
    if user["role"] == "admin":
        account["managed_parking_lots"] = managed_ids(user)
        
    return reply(account)


# 7. user: submit a reservation request
@app.route(API + "/me/reservations", methods=["POST"])
@login_required("user")
def add_reservation(user):
    
    fields = ["parking_id", "vehicle_number", "start_time", "end_time"]
    
    if not all(request.values.get(k) for k in fields):
        return error("Missing required fields", 400)
    
    parking_id, vehicle, start, end = (request.values[k] for k in fields)

    lot = parking_lots.find_one({"parking_id": parking_id})
    
    if lot is None:
        return error("Invalid parking lot ID", 404)

    try:
        start_dt, end_dt = parse_time(start), parse_time(end)
        
    except ValueError:
        return error("Invalid date/time format", 400)
    
    now = datetime.now(timezone.utc)
    
    if start_dt <= now or end_dt <= start_dt:
        return error("Invalid reservation time", 400)

    if any(r["status"] == "pending" for r in user.get("reservation_details", [])):
        return error("You already have a pending reservation", 409)
    
    if count_taken(lot, start_dt, end_dt) >= lot["total_spaces"]:
        return error("No free space at that time", 409)

    reservation_id = next_id("R", 6, [r["reservation_id"] for r in all_reservations()])
    reservation = {
        "reservation_id": reservation_id,
        "parking_id": parking_id,
        "vehicle_number": vehicle,
        "start_time": start,
        "end_time": end,
        "status": "pending",
        "created_at": now.strftime(TIME_FORMAT),
        "sessions": []}
    
    lot_copy = {**reservation, "user_id": user["user_id"]}

    users.update_one({"user_id": user["user_id"]},
                     {"$push": {"reservation_details": reservation}})
    
    parking_lots.update_one({"parking_id": parking_id},
                            {"$push": {"reservations": lot_copy}})
    
    users.update_many(
        {"role": "admin", "managed_parking_lots.parking_id": parking_id},
        {"$push": {"managed_parking_lots.$[m].reservation_refs": lot_copy}},
        array_filters=[{"m.parking_id": parking_id}])

    return reply({"reservation_id": reservation_id, "status": "pending",
                  "url": request.host_url + "api/v1.0/me/reservations/" + reservation_id}, 201)


# 8. view own reservations
@app.route(API + "/me/reservations", methods = ['GET'])
@login_required("user")
def show_my_reservations(user):
    reservations = user.get("reservation_details", [])
    status = request.args.get("status")
    
    if status:
        if status not in ALL_STATUSES:
            return reply({"error": "Invalid status", "allowed_statuses": ALL_STATUSES}, 400)
        
        reservations = [r for r in reservations if r["status"] == status]
    return reply(reservations)


# 9. view one specific own reservation
@app.route(API + "/me/reservations/<reservation_id>", methods = ['GET'])
@login_required("user")
def show_one_reservation(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    
    if reservation is None:
        return error("Invalid reservation ID", 404)
    return reply(reservation)


# 10. update reservation
@app.route(API + "/me/reservations/<reservation_id>", methods=["PUT"])
@login_required("user")
def update_reservation(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    
    if reservation is None:
        return error("Invalid reservation ID", 404)

    vehicle = request.values.get("vehicle_number")
    start = request.values.get("start_time")
    end = request.values.get("end_time")
    
    if vehicle is None and start is None and end is None:
        return error("No update details provided", 400)
    if vehicle is not None and not vehicle.strip():
        return error("Vehicle number cannot be empty", 400)

    if reservation["status"] not in ["pending", "approved"]:
        return error("Only pending or approved reservations can be updated", 409)
    if reservation["status"] == "approved" and (start is not None or end is not None):
        return error("Approved reservations can only update the vehicle number", 409)

    changes = {}
    if vehicle is not None:
        changes["vehicle_number"] = vehicle.strip()

    # only pending reservations can change their times
    if start is not None or end is not None:
        new_start = start if start is not None else reservation["start_time"]
        new_end = end if end is not None else reservation["end_time"]
        try:
            start_dt, end_dt = parse_time(new_start), parse_time(new_end)
        except ValueError:
            return error("Invalid date/time format", 400)
        if start_dt <= datetime.now(timezone.utc) or end_dt <= start_dt:
            return error("Start time must be in the future and before end time", 400)

        lot = parking_lots.find_one({"parking_id": reservation["parking_id"]})
        if lot is None:
            return error("Parking lot not found", 404)
        if count_taken(lot, start_dt, end_dt, ignore_id=reservation_id) >= lot["total_spaces"]:
            return error("No free space at that time", 409)
        changes.update(start_time=new_start, end_time=new_end)

    update_everywhere(reservation_id, user["user_id"], reservation["parking_id"], changes)
    return reply({"message": "Reservation updated successfully",
                  "url": request.host_url + "api/v1.0/me/reservations/" + reservation_id})


# 11. Cancel reservation
@app.route(API + "/me/reservations/<reservation_id>/cancel", methods=["PUT"])
@login_required("user")
def cancel_reservation(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    
    if reservation is None:
        return error("Invalid reservation ID", 404)
    if reservation["status"] not in ["pending", "approved"]:
        return error("Only a pending or approved reservation can be cancelled", 409)

    update_everywhere(reservation_id, user["user_id"], reservation["parking_id"],
                      {"status": "cancelled"})
    return reply({"message": "Reservation cancelled", "status": "cancelled"})







# --------------------- check-in and check-out ----------------------
def start_session(reservation, owner):
    
    #Check a vehicle in. Returns (session, None) or (None, error_response).
    if reservation["status"] != "approved":
        return None, error("Only an approved reservation can be checked in", 409)
    if any(r["status"] == "active" for r in owner.get("reservation_details", [])):
        return None, error("This driver is already checked in", 409)

    lot = parking_lots.find_one({"parking_id": reservation["parking_id"]})
    if lot is None:
        return None, error("Parking lot not found", 404)

    inside = vehicles_inside(lot)
    if len(inside) >= lot["total_spaces"]:
        return None, error("No available parking spaces", 409)
    if find_item(inside, "reservation_id", reservation["reservation_id"]):
        return None, error("This vehicle is already checked in", 409)

    now = now_str()
    session_ids = [s["session_id"] for r in all_reservations() for s in r.get("sessions", [])]
    session = {
        "session_id": next_id("S", 6, session_ids),
        "total_cost": None,
        "movements": [{"check_in_time": now, "check_out_time": None}]}

    update_everywhere(reservation["reservation_id"], owner["user_id"], lot["parking_id"],
                      {"status": "active", "sessions": reservation.get("sessions", []) + [session]})

    inside = inside + [{"reservation_id": reservation["reservation_id"],
                        "vehicle_number": reservation["vehicle_number"]}]
    save_availability(lot["parking_id"], lot["total_spaces"], inside, now)
    return session, None



def end_session(reservation, user_id, session_id):
    if reservation["status"] != "active":
        return None, error(
            "Only an active reservation can be checked out", 409
        )

    lot = parking_lots.find_one(
        {"parking_id": reservation["parking_id"]}
    )
    if lot is None:
        return None, error("Parking lot not found", 404)

    sessions = reservation.get("sessions", [])
    session = next(
        (s for s in sessions if s["session_id"] == session_id),
        None
    )
    if session is None:
        return None, error("Invalid session ID", 404)

    movements = session.get("movements", [])
    if not movements:
        return None, error("No parking movements found", 409)

    if movements[-1]["check_out_time"] is not None:
        return None, error("This session has already been checked out", 409)

    now = now_str()
    seconds = 0

    for movement in movements:
        if movement["check_out_time"] is None:
            movement["check_out_time"] = now

        seconds += (
            parse_time(movement["check_out_time"])
            - parse_time(movement["check_in_time"])
        ).total_seconds()

    session["total_cost"] = round(
        seconds / 3600 * lot["price_per_hour"], 2
    )

    update_everywhere(
        reservation["reservation_id"],
        user_id,
        lot["parking_id"],
        {
            "status": "completed",
            "sessions": sessions
        }
    )

    inside = [
        v for v in vehicles_inside(lot)
        if v["reservation_id"] != reservation["reservation_id"]
    ]

    earned = sum(s["total_cost"] or 0 for s in sessions)

    save_availability(
        lot["parking_id"],
        lot["total_spaces"],
        inside,
        now,
        {
            "income.total_income": round(
                lot["income"]["total_income"] + earned, 2
            ),
            "income.completed_reservations":
                lot["income"]["completed_reservations"] + 1,
            "income.updated_at": now
        }
    )

    return session, None



# 12. Check in
@app.route(API + "/me/reservations/<reservation_id>/sessions/check-in", methods=["POST"])
@login_required("user")
def check_in(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    if reservation is None:
        return error("Invalid reservation ID", 404)

    session, problem = start_session(reservation, user)
    if problem:
        return problem
    return reply({"message": "Checked in successfully", "session": session}, 201)


#13. Check out
@app.route(API + "/me/reservations/<reservation_id>/sessions/<session_id>/check-out", methods=["POST"])
@login_required("user")
def check_out(user, reservation_id, session_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    if reservation is None:
        return error("Invalid reservation ID", 404)
    

    session = next(
        (s for s in reservation.get("sessions", [])
         if s["session_id"] == session_id),
        None
    )


    if session is None:
        return error("Invalid session ID", 404)


    session, problem = end_session(reservation, user["user_id"], session_id)
    if problem:
        return problem
    return reply({"message": "Checked out successfully", "session": session})


# 14. view session history
@app.route(API + "/me/reservations/<reservation_id>/sessions/history", methods= ['GET'])
@login_required("user")
def sessions_history(user, reservation_id):
    history = []
    reservation = find_item(
        user.get("reservation_details", []),
        "reservation_id",
        reservation_id
    )

    if reservation is None:
        return error("Invalid reservation ID", 404)

    for session in reservation.get("sessions", []):
        history.append({
            "reservation_id": reservation["reservation_id"],
            "parking_id": reservation["parking_id"],
            "session_id": session["session_id"],
            "total_cost": session["total_cost"],
            "movements": session["movements"]
        })

    return reply(history)


# 15. get recommendat lots: /recommendations?lat=51.51&lng=-0.13&radius=5
@app.route(API + "/me/recommendations", methods= ["GET"])
@login_required()
def recommendations(user):
    lat, lng, radius, problem = read_location()
    if problem:
        return problem

    nearby = parking_lots.find({
        "num_available_spaces": {"$gt": 0},
        "location": {"$near": {
            "$geometry": {"type": "Point", "coordinates": [lng, lat]},
            "$maxDistance": radius * 1000}}})

    options = []
    for lot in nearby:
        lot_lng, lot_lat = lot["location"]["coordinates"]
        options.append((lot, distance_km(lat, lng, lot_lat, lot_lng)))
    if not options:
        return reply([])

    # scale distance and price against the worst option (1 avoids dividing by 0)
    farthest = max(d for _, d in options) or 1
    dearest = max(lot["price_per_hour"] for lot, _ in options) or 1

    results = []
    for lot, distance in options:
        score = (0.4 * (1 - distance / farthest)
                 + 0.3 * (1 - lot["price_per_hour"] / dearest)
                 + 0.3 * lot["num_available_spaces"] / lot["total_spaces"])
        results.append({
            "parking_id": lot["parking_id"],
            "distance_km": round(distance, 2),
            "price_per_hour": lot["price_per_hour"],
            "num_available_spaces": lot["num_available_spaces"],
            "score": round(score, 2)})

    results.sort(key=lambda item: item["score"], reverse=True)
    return reply(results[:5])


# -------------------------- admin: lots --------------------------------

#Merge the request values over current, convert and validate them. and Returns (values, None) or (None, error_response)

def read_lot_form(current):

    values = {f: request.values.get(f, current.get(f)) for f in LOT_FIELDS}
    for field, value in values.items():
        if value in (None, ""):
            return None, error("Missing required field: " + field, 400)
    try:
        values["latitude"] = float(values["latitude"])
        values["longitude"] = float(values["longitude"])
        values["price_per_hour"] = float(values["price_per_hour"])
        values["total_spaces"] = int(values["total_spaces"])
    except ValueError:
        return None, error("Latitude, longitude, price and spaces must be numbers", 400)

    if not -90 <= values["latitude"] <= 90:
        return None, error("Invalid latitude", 400)
    if not -180 <= values["longitude"] <= 180:
        return None, error("Invalid longitude", 400)
    if values["price_per_hour"] <= 0:
        return None, error("Price must be greater than zero", 400)
    if not 6 <= values["total_spaces"] <= 30:
        return None, error("Total spaces must be between 6 and 30", 400)
    return values, None

#Find a lot and make sure this admin manages it. Returns (lot, error_response)
def get_managed_lot(admin, parking_id):

    lot = parking_lots.find_one({"parking_id": parking_id})
    if lot is None:
        return None, error("Invalid parking lot ID", 404)
    if parking_id not in managed_ids(admin):
        return None, error("You do not manage this parking lot", 403)
    return lot, None


# 16. admin: parking lots addings
@app.route(API + "/parking_lots", methods=["POST"])
@login_required("admin")
def add_parking_lot(admin):
    values, problem = read_lot_form({})
    if problem:
        return problem
    if len(managed_ids(admin)) >= 7:
        return error("An admin can manage at most 7 parking lots", 409)

    new_id = next_id("P", 4, [lot["parking_id"] for lot in parking_lots.find({}, {"parking_id": 1})])
    now = now_str()
    spaces = values["total_spaces"]

    parking_lots.insert_one({
        "parking_id": new_id,
        "address": {"street": values["street"], "city": values["city"],
                    "postcode": values["postcode"]},
        "location": {"type": "Point",
                     "coordinates": [values["longitude"], values["latitude"]]},
        "total_spaces": spaces,
        "num_available_spaces": spaces,
        "updated_at": now,
        "price_per_hour": values["price_per_hour"],
        "administrators": [{"user_id": admin["user_id"], "name": admin["name"]}],
        "reservations": [],
        "income": {"total_income": 0.0, "completed_reservations": 0, "updated_at": now},
        "availability_history": [{"updated_at": now, "num_available_spaces": spaces,
                                  "vehicles_inside": []}]})
    users.update_one({"user_id": admin["user_id"]},
                     {"$push": {"managed_parking_lots": {"parking_id": new_id,
                                                         "reservation_refs": []}}})

    return reply({"message": "Parking lot created", "parking_id": new_id,
                  "url": request.host_url + "api/v1.0/parking_lots/" + new_id}, 201)


#17. update parking lot
@app.route(API + "/parking_lots/<parking_id>", methods=["PUT"])
@login_required("admin")
def edit_parking_lot(admin, parking_id):
    lot, problem = get_managed_lot(admin, parking_id)
    if problem:
        return problem
    if not any(field in request.values for field in LOT_FIELDS):
        return error("Provide at least one field to update", 400)

    longitude, latitude = lot["location"]["coordinates"]
    current = {**lot["address"], "latitude": latitude, "longitude": longitude,
               "total_spaces": lot["total_spaces"], "price_per_hour": lot["price_per_hour"]}
    values, problem = read_lot_form(current)
    if problem:
        return problem

    inside = vehicles_inside(lot)
    if values["total_spaces"] < len(inside):
        return error("Total spaces cannot be lower than vehicles currently parked", 409)

    save_availability(parking_id, values["total_spaces"], inside, now_str(), {
        "address.street": values["street"],
        "address.city": values["city"],
        "address.postcode": values["postcode"],
        "location.coordinates": [values["longitude"], values["latitude"]],
        "price_per_hour": values["price_per_hour"],
        "total_spaces": values["total_spaces"]})

    return reply({"message": "Parking lot updated", "parking_id": parking_id,
                  "url": request.host_url + "api/v1.0/parking_lots/" + parking_id})


# 18. Delete lot
@app.route(API + "/parking_lots/<parking_id>", methods=["DELETE"])
@login_required("admin")
def delete_parking_lot(admin, parking_id):
    lot, problem = get_managed_lot(admin, parking_id)
    if problem:
        return problem
    if lot.get("reservations"):
        return error("This parking lot has reservations and cannot be deleted", 409)

    parking_lots.delete_one({"parking_id": parking_id})
    users.update_many({"role": "admin"},
                      {"$pull": {"managed_parking_lots": {"parking_id": parking_id}}})
    return reply({"message": "Parking lot deleted successfully"})


# ------------------------- admin: reservations ----------------------------
def get_managed_reservation(admin, reservation_id, parking_id):
    #Find a reservation inside the lots. Returns (lot, reservation, error_response).

    lot = parking_lots.find_one({"parking_id": parking_id})

    if lot is None:
        return None, None, error("Invalid parking lot ID", 404)

    if parking_id not in managed_ids(admin):
        return None, None, error(
            "You do not manage this parking lot", 403
        )

    reservation = find_item(
        lot.get("reservations", []),
        "reservation_id",
        reservation_id
    )

    if reservation is None:
        return None, None, error("Invalid reservation ID", 404)

    return lot, reservation, None




# ------- missed from proposal ----------

# 25. Admin: view parking lots managed by the logged-in admin
@app.route(API + "/admin/parking_lots", methods=["GET"])
@login_required("admin")
def admin_show_parking_lots(admin):
    lot_ids = managed_ids(admin)

    lots = parking_lots.find(
        {"parking_id": {"$in": lot_ids}},
        {
            "_id": 0,
            "parking_id": 1,
            "address": 1,
            "location": 1,
            "total_spaces": 1,
            "num_available_spaces": 1,
            "updated_at": 1,
            "price_per_hour": 1
        }
    ).sort("parking_id", 1)

    return reply(list(lots))





# 26. Admin: view one specific managed parking lot
@app.route(API + "/admin/parking_lots/<parking_id>", methods=["GET"])
@login_required("admin")
def admin_show_one_parking_lot(admin, parking_id):
    lot = parking_lots.find_one(
        {"parking_id": parking_id},
        {
            "_id": 0,
            "parking_id": 1,
            "address": 1,
            "location": 1,
            "total_spaces": 1,
            "num_available_spaces": 1,
            "updated_at": 1,
            "price_per_hour": 1
        }
    )

    if lot is None:
        return error("Invalid parking lot ID", 404)

    if parking_id not in managed_ids(admin):
        return error("You do not manage this parking lot", 403)

    return reply(lot)





# 19. admin: view reservations
@app.route(API + "/admin/parking_lots/<parking_id>/reservations")
@login_required("admin")
def admin_show_reservations(admin, parking_id):

    lot = parking_lots.find_one({"parking_id": parking_id})

    if lot is None:
        return error("Invalid parking lot ID", 404)


    if parking_id not in managed_ids(admin):
        return error("You do not manage this parking lot", 403)

    # Validate pagination
    try:
        page, size = get_paging()
    except ValueError:
        return error("pn and ps must be positive numbers", 400)


    reservations = lot.get("reservations", [])


    status = request.args.get("status")
    if status:
        if status not in ALL_STATUSES:
            return reply({
                "error": "Invalid status",
                "allowed_statuses": ALL_STATUSES
            }, 400)

        reservations = [
            r for r in reservations
            if r["status"] == status
        ]

    # Apply pagination
    start = (page - 1) * size
    return reply(reservations[start:start + size])


# 20. admin: update one specefic reservation
@app.route(API + "/admin/parking_lots/<parking_id>/reservations/<reservation_id>", methods=["PUT"])
@login_required("admin")
def admin_update_reservation(admin, reservation_id, parking_id):
    _, reservation, problem = get_managed_reservation(admin, reservation_id, parking_id)
    if problem:
        return problem

    status = request.values.get("status")
    vehicle = request.values.get("vehicle_number")
    if status is None and vehicle is None:
        return error("Provide a status or vehicle number to update", 400)

    changes = {}
    if status is not None:
        if status not in ["approved", "rejected"]:
            return error("Status must be approved or rejected", 400)
        if reservation["status"] != "pending":
            return error("Only pending reservations can be approved or rejected", 409)
        changes["status"] = status

    if vehicle is not None:
        if not vehicle.strip():
            return error("Vehicle number cannot be empty", 400)
        if reservation["status"] not in ["pending", "approved"]:
            return error("Vehicle number can only be changed for pending or approved reservations", 409)
        changes["vehicle_number"] = vehicle.strip()

    update_everywhere(reservation_id, reservation["user_id"], reservation["parking_id"], changes)
    return reply({"message": "Reservation updated successfully",
                  "reservation_id": reservation_id, "changes": changes})


# 21. check-in management
@app.route(API + "/admin/parking_lots/<parking_id>/reservations/<reservation_id>/check-in", methods=["POST"])
@login_required("admin")
def admin_check_in(admin, reservation_id, parking_id):
    _, reservation, problem = get_managed_reservation(admin, reservation_id, parking_id)
    if problem:
        return problem

    
    owner = users.find_one({"user_id": reservation["user_id"]})
    if owner is None:
        return error("Reservation owner not found", 404)

    session, problem = start_session(reservation, owner)
    if problem:
        return problem
    return reply({"message": "Vehicle checked in by admin", "session": session}, 201)


# 22. checkout management
@app.route(API + "/admin/parking_lots/<parking_id>/reservations/<reservation_id>/sessions/<session_id>/check-out", methods=["POST"])
@login_required("admin")
def admin_check_out(admin, reservation_id, session_id, parking_id):
    _, reservation, problem = get_managed_reservation(admin, reservation_id, parking_id)
    if problem:
        return problem

    session, problem = end_session(reservation, reservation["user_id"], session_id)
    if problem:
        return problem
    return reply({"message": "Parking session completed by admin", "session": session})


# 23. admin: occupancy
@app.route(API + "/admin/occupancy", methods= ["GET"])
@login_required("admin")
def occupancy(admin):
    results = []
    for lot in parking_lots.find({"parking_id": {"$in": managed_ids(admin)}}):
        occupied = lot["total_spaces"] - lot["num_available_spaces"]
        results.append({
            "parking_id": lot["parking_id"],
            "total_spaces": lot["total_spaces"],
            "occupied_spaces": occupied,
            "num_available_spaces": lot["num_available_spaces"],
            "occupancy_rate": round(occupied / lot["total_spaces"] * 100, 1),
            "vehicles_inside": vehicles_inside(lot)})
    return reply(results)


#24. admin: revenue
@app.route(API + "/admin/revenue", methods= ["GET"])
@login_required("admin")
def revenue(admin):
    by_lot = [{"parking_id": lot["parking_id"],
               "total_income": lot["income"]["total_income"],
               "completed_reservations": lot["income"]["completed_reservations"]}
              for lot in parking_lots.find({"parking_id": {"$in": managed_ids(admin)}})]

    return reply({
        "total_revenue": round(sum(lot["total_income"] for lot in by_lot), 2),
        "completed_reservations": sum(lot["completed_reservations"] for lot in by_lot),
        "by_parking_lot": by_lot})


if __name__ == "__main__":
    app.run(debug=True, port=5001)