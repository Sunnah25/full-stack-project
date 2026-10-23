from flask import Blueprint

from auth_utils import login_required
from helpers import end_session, error, find_item, reply, start_session

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/v1.0/me/reservations")


# 12. Check in
@sessions_bp.route("/<reservation_id>/sessions/check-in", methods=["POST"])
@login_required("user")
def check_in(user, reservation_id):
    reservation = find_item(user.get("reservation_details", []), "reservation_id", reservation_id)
    if reservation is None:
        return error("Invalid reservation ID", 404)

    session, problem = start_session(reservation, user)
    if problem:
        return problem
    return reply({"message": "Checked in successfully", "session": session}, 201)


# 13. Check out
@sessions_bp.route("/<reservation_id>/sessions/<session_id>/check-out", methods=["POST"])
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


# 14. View session history
@sessions_bp.route("/<reservation_id>/sessions/history", methods=["GET"])
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