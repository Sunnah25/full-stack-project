from flask import request

from flask import Blueprint

from auth_utils import login_required
from extensions import users, parking_lots
from helpers import (ALL_STATUSES, end_session, error, get_managed_reservation,
                     get_paging, managed_ids, reply, start_session,
                     vehicles_inside)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1.0/admin")


# 25. Admin: view parking lots managed by the logged-in admin
@admin_bp.route("/parking_lots", methods=["GET"])
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
@admin_bp.route("/parking_lots/<parking_id>", methods=["GET"])
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


# 19. Admin: view reservations
@admin_bp.route("/parking_lots/<parking_id>/reservations", methods=["GET"])
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


# 20. Admin: update one specific reservation
@admin_bp.route("/parking_lots/<parking_id>/reservations/<reservation_id>", methods=["PUT"])
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

    update_everywhere_args = (reservation_id, reservation["user_id"], reservation["parking_id"], changes)
    from helpers import update_everywhere
    update_everywhere(*update_everywhere_args)
    return reply({"message": "Reservation updated successfully",
                  "reservation_id": reservation_id, "changes": changes})


# 21. Admin: check-in management
@admin_bp.route("/parking_lots/<parking_id>/reservations/<reservation_id>/check-in", methods=["POST"])
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


# 22. Admin: check-out management
@admin_bp.route("/parking_lots/<parking_id>/reservations/<reservation_id>/sessions/<session_id>/check-out", methods=["POST"])
@login_required("admin")
def admin_check_out(admin, reservation_id, session_id, parking_id):
    _, reservation, problem = get_managed_reservation(admin, reservation_id, parking_id)
    if problem:
        return problem

    session, problem = end_session(reservation, reservation["user_id"], session_id)
    if problem:
        return problem
    return reply({"message": "Parking session completed by admin", "session": session})


# 23. Admin: occupancy
@admin_bp.route("/occupancy", methods=["GET"])
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


# 24. Admin: revenue
@admin_bp.route("/revenue", methods=["GET"])
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