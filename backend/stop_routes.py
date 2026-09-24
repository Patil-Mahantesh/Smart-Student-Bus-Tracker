from flask import Blueprint, request, jsonify
from auth import role_required
from database import get_connection


stop_bp = Blueprint(
    "stop",
    __name__,
    url_prefix="/api/stops"
)


# ============================================================
# GET ALL STOPS
# ============================================================

@stop_bp.get("")
@role_required("ADMIN")
def get_stops():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                s.id,
                s.route_id,
                r.route_name,
                s.stop_name,
                s.latitude,
                s.longitude,
                s.stop_order,
                s.stop_type,
                s.is_active
            FROM stops s
            JOIN routes r
                ON r.id = s.route_id
            WHERE s.is_active = 1
            ORDER BY
                s.route_id,
                s.stop_order
            """
        ).fetchall()

        stops = []

        for row in rows:

            stops.append({
                "id": row["id"],
                "route_id": row["route_id"],
                "route_name": row["route_name"],
                "stop_name": row["stop_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "stop_order": row["stop_order"],
                "stop_type": row["stop_type"],
                "is_active": row["is_active"],
            })

        return jsonify({
            "success": True,
            "stops": stops
        })

    finally:

        connection.close()


# ============================================================
# CREATE STOP
# ============================================================

@stop_bp.post("")
@role_required("ADMIN")
def create_stop():

    data = request.get_json() or {}

    route_id = data.get("route_id")
    stop_name = str(data.get("stop_name", "")).strip()
    stop_type = str(
        data.get("stop_type", "")
    ).upper().strip()

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    stop_order = data.get("stop_order")

    if not route_id:
        return jsonify({
            "success": False,
            "message": "Route is required."
        }), 400

    if not stop_name:
        return jsonify({
            "success": False,
            "message": "Stop name is required."
        }), 400

    if stop_type not in ("PICKUP", "DROP"):
        return jsonify({
            "success": False,
            "message": "Stop type must be PICKUP or DROP."
        }), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        stop_order = int(stop_order)
        route_id = int(route_id)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid location, route or stop order."
        }), 400

    if not -90 <= latitude <= 90:
        return jsonify({
            "success": False,
            "message": "Invalid latitude."
        }), 400

    if not -180 <= longitude <= 180:
        return jsonify({
            "success": False,
            "message": "Invalid longitude."
        }), 400

    if stop_order < 1:
        return jsonify({
            "success": False,
            "message": "Stop order must be at least 1."
        }), 400

    connection = get_connection()

    try:

        route = connection.execute(
            """
            SELECT id
            FROM routes
            WHERE id = ?
              AND is_active = 1
            """,
            (route_id,)
        ).fetchone()

        if not route:

            return jsonify({
                "success": False,
                "message": "Selected route does not exist."
            }), 404

        # Shift existing stops so the requested order is available.
        connection.execute(
            """
            UPDATE stops
            SET stop_order = stop_order + 1
            WHERE route_id = ?
              AND stop_order >= ?
              AND is_active = 1
            """,
            (
                route_id,
                stop_order
            )
        )

        cursor = connection.execute(
            """
            INSERT INTO stops (
                route_id,
                stop_name,
                latitude,
                longitude,
                stop_order,
                stop_type,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                route_id,
                stop_name,
                latitude,
                longitude,
                stop_order,
                stop_type
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Stop created successfully.",
            "stop_id": cursor.lastrowid
        }), 201

    except Exception as error:

        connection.rollback()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# UPDATE STOP
# ============================================================

@stop_bp.put("/<int:stop_id>")
@role_required("ADMIN")
def update_stop(stop_id):

    data = request.get_json() or {}

    route_id = data.get("route_id")
    stop_name = str(data.get("stop_name", "")).strip()
    stop_type = str(
        data.get("stop_type", "")
    ).upper().strip()

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    stop_order = data.get("stop_order")

    if not route_id or not stop_name:
        return jsonify({
            "success": False,
            "message": "Route and stop name are required."
        }), 400

    if stop_type not in ("PICKUP", "DROP"):
        return jsonify({
            "success": False,
            "message": "Stop type must be PICKUP or DROP."
        }), 400

    try:

        route_id = int(route_id)
        latitude = float(latitude)
        longitude = float(longitude)
        stop_order = int(stop_order)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid stop data."
        }), 400

    connection = get_connection()

    try:

        existing = connection.execute(
            """
            SELECT id
            FROM stops
            WHERE id = ?
              AND is_active = 1
            """,
            (stop_id,)
        ).fetchone()

        if not existing:

            return jsonify({
                "success": False,
                "message": "Stop not found."
            }), 404

        connection.execute(
            """
            UPDATE stops
            SET
                route_id = ?,
                stop_name = ?,
                latitude = ?,
                longitude = ?,
                stop_order = ?,
                stop_type = ?
            WHERE id = ?
            """,
            (
                route_id,
                stop_name,
                latitude,
                longitude,
                stop_order,
                stop_type,
                stop_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Stop updated successfully."
        })

    except Exception as error:

        connection.rollback()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# DELETE STOP
# ============================================================

@stop_bp.delete("/<int:stop_id>")
@role_required("ADMIN")
def delete_stop(stop_id):

    connection = get_connection()

    try:

        stop = connection.execute(
            """
            SELECT id
            FROM stops
            WHERE id = ?
              AND is_active = 1
            """,
            (stop_id,)
        ).fetchone()

        if not stop:

            return jsonify({
                "success": False,
                "message": "Stop not found."
            }), 404

        # Do not delete a stop that is currently assigned
        # to a student.
        student = connection.execute(
            """
            SELECT id
            FROM students
            WHERE
                (pickup_stop_id = ? OR drop_stop_id = ?)
                AND is_active = 1
            LIMIT 1
            """,
            (
                stop_id,
                stop_id
            )
        ).fetchone()

        if student:

            return jsonify({
                "success": False,
                "message":
                    "This stop is assigned to a student and "
                    "cannot be deleted."
            }), 409

        # Soft delete.
        connection.execute(
            """
            UPDATE stops
            SET is_active = 0
            WHERE id = ?
            """,
            (stop_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Stop deleted successfully."
        })

    except Exception as error:

        connection.rollback()

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:

        connection.close()


# ============================================================
# GET STOPS FOR ONE ROUTE
# ============================================================

@stop_bp.get("/route/<int:route_id>")
@role_required("ADMIN")
def get_route_stops(route_id):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                route_id,
                stop_name,
                latitude,
                longitude,
                stop_order,
                stop_type,
                is_active
            FROM stops
            WHERE route_id = ?
              AND is_active = 1
            ORDER BY stop_order
            """,
            (route_id,)
        ).fetchall()

        stops = []

        for row in rows:

            stops.append({
                "id": row["id"],
                "route_id": row["route_id"],
                "stop_name": row["stop_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "stop_order": row["stop_order"],
                "stop_type": row["stop_type"],
                "is_active": row["is_active"],
            })

        return jsonify({
            "success": True,
            "stops": stops
        })

    finally:

        connection.close()