from flask import Blueprint, jsonify, request, g

from auth import token_required
from database import get_connection


location_bp = Blueprint(
    "location",
    __name__,
    url_prefix="/api/locations"
)


# ============================================================
# RECORD DRIVER GPS LOCATION
# ============================================================

@location_bp.post("")
@token_required
def record_location():

    data = request.get_json(silent=True) or {}

    trip_id = data.get("trip_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    speed = data.get("speed")

    if not trip_id:
        return jsonify({
            "success": False,
            "message": "trip_id is required"
        }), 400

    if latitude is None or longitude is None:
        return jsonify({
            "success": False,
            "message": "latitude and longitude are required"
        }), 400

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # Find logged-in driver
        # ----------------------------------------------------

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
                "success": False,
                "message": "Driver profile not found"
            }), 404

        driver_id = driver["id"]

        # ----------------------------------------------------
        # Verify trip
        # ----------------------------------------------------

        trip = connection.execute(
            """
            SELECT
                id,
                driver_id,
                status
            FROM trips
            WHERE id = ?
            """,
            (trip_id,)
        ).fetchone()

        if not trip:
            return jsonify({
                "success": False,
                "message": "Trip not found"
            }), 404

        # ----------------------------------------------------
        # Make sure this driver owns the trip
        # ----------------------------------------------------

        if trip["driver_id"] != driver_id:

            return jsonify({
                "success": False,
                "message": "You are not assigned to this trip"
            }), 403

        # ----------------------------------------------------
        # Trip must be active
        # ----------------------------------------------------

        if trip["status"] != "IN_PROGRESS":

            return jsonify({
                "success": False,
                "message": "Trip is not currently active"
            }), 400

        # ----------------------------------------------------
        # Validate GPS values
        # ----------------------------------------------------

        latitude = float(latitude)
        longitude = float(longitude)

        if speed is not None:
            speed = float(speed)

        # ----------------------------------------------------
        # Store location
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO bus_locations (
                trip_id,
                latitude,
                longitude,
                speed,
                recorded_at
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                trip_id,
                latitude,
                longitude,
                speed
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Bus location recorded successfully",
            "location": {
                "trip_id": trip_id,
                "latitude": latitude,
                "longitude": longitude,
                "speed": speed
            }
        }), 201

    except (TypeError, ValueError):

        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Invalid location data"
        }), 400

    except Exception as error:

        connection.rollback()

        print(
            "Location recording error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to record bus location",
            "error": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# GET LATEST LOCATION FOR A SPECIFIC TRIP
# ============================================================

@location_bp.get("/trip/<int:trip_id>/latest")
@token_required
def get_latest_location(trip_id):

    connection = get_connection()

    try:

        location = connection.execute(
            """
            SELECT
                id,
                trip_id,
                latitude,
                longitude,
                speed,
                recorded_at
            FROM bus_locations
            WHERE trip_id = ?
            ORDER BY recorded_at DESC, id DESC
            LIMIT 1
            """,
            (trip_id,)
        ).fetchone()

        if not location:

            return jsonify({
                "success": True,
                "location": None
            }), 200

        return jsonify({
            "success": True,
            "location": {
                "id": location["id"],
                "trip_id": location["trip_id"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "speed": location["speed"],
                "recorded_at": location["recorded_at"]
            }
        }), 200

    except Exception as error:

        print(
            "Latest location error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to fetch latest bus location",
            "error": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# GET LATEST LOCATION FOR A BUS
#
# Used by Parent/Admin dashboards.
#
# The backend automatically finds the latest active trip
# belonging to the requested bus.
# ============================================================

@location_bp.get("/bus/<int:bus_id>/latest")
@token_required
def get_latest_bus_location(bus_id):

    connection = get_connection()

    try:

        location = connection.execute(
            """
            SELECT
                bl.id,
                bl.trip_id,
                bl.latitude,
                bl.longitude,
                bl.speed,
                bl.recorded_at,
                t.bus_id,
                t.route_id,
                t.trip_type,
                t.status,
                t.started_at
            FROM bus_locations bl

            INNER JOIN trips t
                ON t.id = bl.trip_id

            WHERE t.bus_id = ?
              AND t.id = (
                  SELECT id
                  FROM trips
                  WHERE bus_id = ?
                    AND status = 'IN_PROGRESS'
                  ORDER BY id DESC
                  LIMIT 1
              )

            ORDER BY
                bl.recorded_at DESC,
                bl.id DESC

            LIMIT 1
            """,
            (bus_id, bus_id)
        ).fetchone()

        # ----------------------------------------------------
        # No active bus location
        # ----------------------------------------------------

        if not location:

            return jsonify({
                "success": True,
                "location": None
            }), 200

        # ----------------------------------------------------
        # Return latest live location
        # ----------------------------------------------------

        return jsonify({
            "success": True,
            "location": {
                "id": location["id"],
                "bus_id": location["bus_id"],
                "trip_id": location["trip_id"],
                "route_id": location["route_id"],
                "trip_type": location["trip_type"],
                "status": location["status"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "speed": location["speed"],
                "recorded_at": location["recorded_at"],
                "started_at": location["started_at"]
            }
        }), 200

    except Exception as error:

        print(
            "Latest bus location error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to fetch bus location",
            "error": str(error)
        }), 500

    finally:

        connection.close()