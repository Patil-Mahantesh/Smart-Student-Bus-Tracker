from flask import Blueprint, request, jsonify, g
from datetime import datetime
from zoneinfo import ZoneInfo

from database import get_connection
from auth import role_required


trip_bp = Blueprint(
    "trip",
    __name__,
    url_prefix="/api/trips"
)


# ============================================================
# START TRIP
# ============================================================

@trip_bp.post("/start")
@role_required("DRIVER")
def start_trip():
    data = request.get_json(silent=True) or {}
    trip_type = str(data.get("trip_type", "")).upper()

    if trip_type not in ("PICKUP", "DROP"):
        return jsonify({
            "success": False,
            "message": "Choose either PICKUP or DROP before starting the trip."
        }), 400

    connection = get_connection()
    try:
        driver = connection.execute(
            "SELECT id, name FROM drivers WHERE user_id = ?",
            (g.user["user_id"],)
        ).fetchone()
        if not driver:
            return jsonify({"success": False, "message": "Driver profile not found"}), 404

        assignment = connection.execute(
            """
            SELECT
                b.id AS bus_id,
                b.bus_number,
                b.status AS bus_status,
                b.is_active AS bus_active,
                r.id AS route_id,
                r.route_name,
                r.is_active AS route_active
            FROM driver_bus_assignments dba
            JOIN buses b ON b.id = dba.bus_id
            LEFT JOIN bus_route_assignments bra
                ON bra.bus_id = b.id AND bra.is_active = 1
                AND bra.id = (
                    SELECT MAX(bra2.id)
                    FROM bus_route_assignments bra2
                    WHERE bra2.bus_id = b.id AND bra2.is_active = 1
                )
            LEFT JOIN routes r ON r.id = bra.route_id
            WHERE dba.driver_id = ? AND dba.is_active = 1
            ORDER BY dba.id DESC
            LIMIT 1
            """,
            (driver["id"],)
        ).fetchone()

        if not assignment:
            return jsonify({
                "success": False,
                "message": "No active bus is assigned to this driver. Contact Admin."
            }), 409
        if not assignment["route_id"] or not assignment["route_active"]:
            return jsonify({
                "success": False,
                "message": "No active route is assigned to your bus. Contact Admin."
            }), 409
        if not assignment["bus_active"] or str(assignment["bus_status"]).upper() != "ACTIVE":
            return jsonify({
                "success": False,
                "message": "Your assigned bus is not active. Contact Admin."
            }), 409

        requested_bus_id = data.get("bus_id")
        requested_route_id = data.get("route_id")
        if requested_bus_id not in (None, "") and int(requested_bus_id) != assignment["bus_id"]:
            return jsonify({"success": False, "message": "You can only start a trip using your assigned bus."}), 403
        if requested_route_id not in (None, "") and int(requested_route_id) != assignment["route_id"]:
            return jsonify({"success": False, "message": "You can only start a trip using your bus's assigned route."}), 403

        active_trip = connection.execute(
            """
            SELECT id FROM trips
            WHERE driver_id = ? AND status = 'IN_PROGRESS'
            ORDER BY id DESC LIMIT 1
            """,
            (driver["id"],)
        ).fetchone()
        if active_trip:
            return jsonify({
                "success": False,
                "message": "Driver already has an active trip",
                "trip_id": active_trip["id"]
            }), 409

        trip_date = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        cursor = connection.execute(
            """
            INSERT INTO trips
                (bus_id, route_id, driver_id, trip_type, status, trip_date, started_at)
            VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?, CURRENT_TIMESTAMP)
            """,
            (assignment["bus_id"], assignment["route_id"], driver["id"], trip_type, trip_date)
        )
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Trip started successfully",
            "trip_id": cursor.lastrowid,
            "trip_type": trip_type,
            "status": "IN_PROGRESS",
            "bus": {"id": assignment["bus_id"], "bus_number": assignment["bus_number"]},
            "route": {"id": assignment["route_id"], "route_name": assignment["route_name"]},
            "driver": {"id": driver["id"], "name": driver["name"]}
        }), 201

    except (TypeError, ValueError):
        connection.rollback()
        return jsonify({"success": False, "message": "Invalid bus or route assignment."}), 400
    except Exception as error:
        connection.rollback()
        return jsonify({"success": False, "message": "Failed to start trip", "error": str(error)}), 500
    finally:
        connection.close()


# ============================================================
# GET ACTIVE TRIP
# ============================================================

@trip_bp.get("/active")
@role_required("DRIVER")
def get_active_trip():

    connection = get_connection()

    try:

        driver = connection.execute(
            """
            SELECT id, name
            FROM drivers
            WHERE user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not driver:
            return jsonify({
                "message": "Driver profile not found"
            }), 404

        trip = connection.execute(
            """
            SELECT
                t.id,
                t.bus_id,
                t.route_id,
                t.driver_id,
                t.trip_type,
                t.status,
                t.started_at,
                b.bus_number,
                r.route_name
            FROM trips t
            JOIN buses b
                ON b.id = t.bus_id
            JOIN routes r
                ON r.id = t.route_id
            WHERE t.driver_id = ?
              AND t.status = 'IN_PROGRESS'
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (driver["id"],)
        ).fetchone()

        if not trip:
            return jsonify({
                "active": False,
                "trip": None
            }), 200

        stops = [dict(row) for row in connection.execute(
            """
            SELECT id, route_id, stop_name, stop_type, latitude, longitude,
                   stop_order, scheduled_pickup_time, scheduled_drop_time
            FROM stops
            WHERE route_id = ? AND is_active = 1
            ORDER BY stop_order ASC, id ASC
            """,
            (trip["route_id"],)
        ).fetchall()]

        return jsonify({
            "active": True,
            "trip": {
                "id": trip["id"],
                "bus_id": trip["bus_id"],
                "route_id": trip["route_id"],
                "driver_id": trip["driver_id"],
                "trip_type": trip["trip_type"],
                "status": trip["status"],
                "started_at": trip["started_at"],
                "bus_number": trip["bus_number"],
                "route_name": trip["route_name"],
                "stops": stops
            }
        }), 200

    except Exception as error:

        print("Active trip error:", error)

        return jsonify({
            "message": "Unable to fetch active trip",
            "error": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# STOP TRIP
# ============================================================

@trip_bp.post("/<int:trip_id>/stop")
@role_required("DRIVER")
def stop_trip(trip_id):

    connection = get_connection()

    try:

        trip = connection.execute(
            """
            SELECT
                id,
                status,
                driver_id
            FROM trips
            WHERE id = ?
            """,
            (trip_id,)
        ).fetchone()

        if not trip:
            return jsonify({
                "message": "Trip not found"
            }), 404

        driver = connection.execute(
            """
            SELECT id
            FROM drivers
            WHERE user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not driver:
            return jsonify({
                "message": "Driver profile not found"
            }), 404

        if trip["driver_id"] != driver["id"]:
            return jsonify({
                "message": "You are not authorized to stop this trip"
            }), 403

        if trip["status"] != "IN_PROGRESS":
            return jsonify({
                "message": "Trip is not currently in progress"
            }), 400

        connection.execute(
            """
            UPDATE trips
            SET
                status = 'COMPLETED',
                ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (trip_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Trip completed successfully",
            "trip_id": trip_id,
            "status": "COMPLETED"
        }), 200

    except Exception as error:

        connection.rollback()

        return jsonify({
            "message": "Failed to stop trip",
            "error": str(error)
        }), 500

    finally:

        connection.close()