from datetime import datetime, timezone

from flask import Blueprint, request

from auth_utils import login_required
from extensions import users, parking_lots
from helpers import (ALL_STATUSES, TIME_FORMAT, all_reservations, count_taken,
                     distance_km, error, find_item, next_id, parse_time,
                     read_location, reply, update_everywhere)

reservations_bp = Blueprint("reservations", __name__, url_prefix="/api/v1.0/me")


# 7. User: submit a reservation request
@reservations_bp.route("/reservations", methods=["POST"])
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


# 8. View own reservations
@reservations_bp.route("/reservations", methods=["GET"])
@login_required("user")
def show_my_reservations(user):
    reservations = user.get("reservation_details", [])
    status = request.args.get("status")

    if status:
        if status not in ALL_STATUSES:
            return reply({"error": "Invalid status", "allowed_statuses": ALL_STATUSES}, 400)

        reservations = [r for r in reservations if r["status"] == status]
    return reply(reservations)


# 9. View one specific own reservation
@reservations_bp.route("/reservations/<reservation_id>", methods=["GET"])
@login_required("user")
def show_one_reservation(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)

    if reservation is None:
        return error("Invalid reservation ID", 404)
    return reply(reservation)


# 10. Update reservation
@reservations_bp.route("/reservations/<reservation_id>", methods=["PUT"])
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
@reservations_bp.route("/reservations/<reservation_id>/cancel", methods=["PUT"])
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


# 15. Get recommended lots: /me/recommendations?lat=51.51&lng=-0.13&radius=5
@reservations_bp.route("/recommendations", methods=["GET"])
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