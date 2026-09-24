from flask import Blueprint, request, jsonify, g

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

    data = request.get_json() or {}

    bus_id = data.get("bus_id")
    route_id = data.get("route_id")
    trip_type = data.get("trip_type")

    if not bus_id or not route_id or not trip_type:
        return jsonify({
            "message": "bus_id, route_id and trip_type are required"
        }), 400

    if trip_type not in ["PICKUP", "DROP"]:
        return jsonify({
            "message": "Invalid trip type"
        }), 400

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

        driver_id = driver["id"]

        active_trip = connection.execute(
            """
            SELECT id
            FROM trips
            WHERE driver_id = ?
              AND status = 'IN_PROGRESS'
            """,
            (driver_id,)
        ).fetchone()

        if active_trip:
            return jsonify({
                "message": "Driver already has an active trip",
                "trip_id": active_trip["id"]
            }), 409

        bus = connection.execute(
            """
            SELECT id, bus_number
            FROM buses
            WHERE id = ?
            """,
            (bus_id,)
        ).fetchone()

        if not bus:
            return jsonify({
                "message": "Bus not found"
            }), 404

        route = connection.execute(
            """
            SELECT id, route_name
            FROM routes
            WHERE id = ?
            """,
            (route_id,)
        ).fetchone()

        if not route:
            return jsonify({
                "message": "Route not found"
            }), 404

        cursor = connection.execute(
            """
            INSERT INTO trips
            (
                bus_id,
                route_id,
                driver_id,
                trip_type,
                status,
                started_at
            )
            VALUES (?, ?, ?, ?, 'IN_PROGRESS', CURRENT_TIMESTAMP)
            """,
            (
                bus_id,
                route_id,
                driver_id,
                trip_type
            )
        )

        connection.commit()

        return jsonify({
            "message": "Trip started successfully",
            "trip_id": cursor.lastrowid,
            "trip_type": trip_type,
            "status": "IN_PROGRESS",
            "bus": {
                "id": bus["id"],
                "bus_number": bus["bus_number"]
            },
            "route": {
                "id": route["id"],
                "route_name": route["route_name"]
            },
            "driver": {
                "id": driver["id"],
                "name": driver["name"]
            }
        }), 201

    except Exception as error:

        connection.rollback()

        return jsonify({
            "message": "Failed to start trip",
            "error": str(error)
        }), 500

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
                "route_name": trip["route_name"]
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