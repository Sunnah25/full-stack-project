from flask import Blueprint, request

from auth_utils import login_required
from extensions import users, parking_lots
from helpers import (count_taken, distance_km, error, get_managed_lot, get_paging,
                     LOT_FIELDS, LOT_SUMMARY, managed_ids, next_id, now_str,
                     parse_time, read_location, read_lot_form, reply,
                     save_availability, vehicles_inside)

parking_lots_bp = Blueprint("parking_lots", __name__, url_prefix="/api/v1.0/parking_lots")


# 1. View parking lots
@parking_lots_bp.route("", methods=["GET"])
def show_all_parking_lots():
    try:
        page, size = get_paging()
    except ValueError:
        return error("pn and ps must be positive numbers", 400)

    lots = parking_lots.find().sort("parking_id", 1).skip((page - 1) * size).limit(size)
    return reply([{field: lot[field] for field in LOT_SUMMARY} for lot in lots])


# 2. View one specific parking lot
@parking_lots_bp.route("/<parking_id>", methods=["GET"])
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
@parking_lots_bp.route("/search", methods=["GET"])
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


# 16. Admin: add parking lot
@parking_lots_bp.route("", methods=["POST"])
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


# 17. Admin: update parking lot
@parking_lots_bp.route("/<parking_id>", methods=["PUT"])
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


# 18. Admin: delete parking lot
@parking_lots_bp.route("/<parking_id>", methods=["DELETE"])
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