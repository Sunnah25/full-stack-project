import hashlib
from datetime import datetime, timezone
from math import cos, radians
from flask import jsonify, make_response, request

from extensions import users, parking_lots


API = "/api/v1.0"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FREE_STATUSES = ["cancelled", "rejected"]
ALL_STATUSES = ["pending", "approved", "rejected", "active", "completed", "cancelled"]
LOT_FIELDS = ["street", "city", "postcode", "latitude", "longitude",
              "total_spaces", "price_per_hour"]
LOT_SUMMARY = ["parking_id", "address", "location", "total_spaces",
               "num_available_spaces", "updated_at", "price_per_hour"]







# helper functions

# error response
def error(message, code):
    return make_response(jsonify({"error": message}), code)

# good response
def reply(body, code=200):
    return make_response(jsonify(body), code)

# time
def now_str():
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


#ISO string = timezone aware datetime (raises ValueError if invalid)
def parse_time(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("timezone missing")
    return value


# to make hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


#First dict in a list where item[key] == value, else None.
def find_item(items, key, value):
    return next((item for item in items if item[key] == value), None)


# paginations
def get_paging():
    page = int(request.args.get("pn", 1))
    size = int(request.args.get("ps", 10))
    if page < 1 or size < 1:
        raise ValueError("bad paging")
    return page, size


#calculate distances
def distance_km(lat1, lng1, lat2, lng2):
    dy = (lat2 - lat1) * 111
    dx = (lng2 - lng1) * 111 * cos(radians(lat1))
    return (dx ** 2 + dy ** 2) ** 0.5


# get user location
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


# to generate next id number for reservation and session.
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









# admin / lot helpers

# Merge the request values over current, convert and validate them.
# Returns (values, None) or (None, error_response)
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




# It should find a lot managed by this admin. Returns (lot, error_response)
def get_managed_lot(admin, parking_id):
 
    lot = parking_lots.find_one({"parking_id": parking_id})
    
    if lot is None:
        return None, error("Invalid parking lot ID", 404)
    
    if parking_id not in managed_ids(admin):
        return None, error("You do not manage this parking lot", 403)
    
    return lot, None



# It finds a reservation inside the lots. Returns (lot, reservation, error_response).
def get_managed_reservation(admin, reservation_id, parking_id):
    lot = parking_lots.find_one({"parking_id": parking_id})
    
    if lot is None:
        return None, None, error("Invalid parking lot ID", 404)
    
    if parking_id not in managed_ids(admin):
        return None, None, error("You do not manage this parking lot", 403)

    reservation = find_item(lot.get("reservations", []), "reservation_id", reservation_id)
    
    if reservation is None:
        return None, None, error("Invalid reservation ID", 404)

    return lot, reservation, None




# check-in and check-out logic

# Check a vehicle in. Returns (session, None) or (None, error_response).
def start_session(reservation, owner):
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
        return None, error("Only an active reservation can be checked out", 409)

    lot = parking_lots.find_one({"parking_id": reservation["parking_id"]})
    
    if lot is None:
        return None, error("Parking lot not found", 404)

    sessions = reservation.get("sessions", [])
    
    session = next((s for s in sessions if s["session_id"] == session_id), None)
    
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

    session["total_cost"] = round(seconds / 3600 * lot["price_per_hour"], 2)

    update_everywhere(reservation["reservation_id"], user_id, lot["parking_id"],
                      {"status": "completed", "sessions": sessions})

    inside = [v for v in vehicles_inside(lot)
              if v["reservation_id"] != reservation["reservation_id"]]

    earned = sum(s["total_cost"] or 0 for s in sessions)

    save_availability(
        lot["parking_id"],
        lot["total_spaces"],
        inside,
        now,
        {
            "income.total_income": round(lot["income"]["total_income"] + earned, 2),
            "income.completed_reservations": lot["income"]["completed_reservations"] + 1,
            "income.updated_at": now
        })

    return session, None