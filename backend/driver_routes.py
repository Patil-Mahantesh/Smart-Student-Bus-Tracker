from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash

from auth import role_required
from database import get_connection


driver_bp = Blueprint(
    "driver",
    __name__,
    url_prefix="/api/drivers"
)


# ============================================================
# CREATE DRIVER
# ============================================================

@driver_bp.post("")
@role_required("ADMIN")
def create_driver():

    data = request.get_json(silent=True) or {}

    username = data.get("username")
    password = data.get("password")
    name = data.get("name")
    phone = data.get("phone")
    license_number = data.get("license_number")

    if not username or not password or not name:
        return jsonify({
            "success": False,
            "message": "Username, password and name are required."
        }), 400

    connection = get_connection()

    try:

        password_hash = generate_password_hash(password)

        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role
            )
            VALUES (?, ?, ?)
            """,
            (username, password_hash, "DRIVER")
        )

        user_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO drivers (
                user_id,
                name,
                phone,
                license_number
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                phone,
                license_number
            )
        )

        driver_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Driver created successfully.",
            "driver_id": driver_id
        }), 201

    except Exception as error:

        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not create driver.",
            "error": str(error)
        }), 409

    finally:
        connection.close()


# ============================================================
# GET LOGGED-IN DRIVER ASSIGNMENT
# BUS + ROUTE + ROUTE STOPS
# ============================================================

@driver_bp.get("/assignment")
@role_required("DRIVER")
def get_driver_assignment():

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # 1. GET LOGGED-IN DRIVER
        # ----------------------------------------------------

        driver = connection.execute(
            """
            SELECT
                id,
                name,
                phone,
                license_number
            FROM drivers
            WHERE user_id = ?
              AND is_active = 1
            LIMIT 1
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not driver:

            return jsonify({
                "success": False,
                "message": "Driver profile not found or inactive.",
                "driver": None,
                "bus": None,
                "route": None,
                "stops": [],
                "has_active_route": False
            }), 404

        driver_data = dict(driver)

        # ----------------------------------------------------
        # 2. GET DRIVER'S ACTIVE BUS
        # ----------------------------------------------------

        bus_assignment = connection.execute(
            """
            SELECT
                dba.id AS assignment_id,
                dba.assigned_from,
                dba.assigned_until,
                dba.is_active AS assignment_is_active,

                b.id AS bus_id,
                b.bus_number,
                b.registration_number,
                b.capacity,
                b.status AS bus_status,
                b.is_active AS bus_is_active

            FROM driver_bus_assignments dba

            JOIN buses b
                ON b.id = dba.bus_id

            WHERE dba.driver_id = ?
              AND dba.is_active = 1
              AND b.is_active = 1

            ORDER BY dba.id DESC
            LIMIT 1
            """,
            (driver["id"],)
        ).fetchone()

        if not bus_assignment:

            return jsonify({
                "success": False,
                "message": "No active bus assigned to this driver.",
                "driver": driver_data,
                "bus": None,
                "route": None,
                "stops": [],
                "has_active_route": False
            }), 200

        bus_id = bus_assignment["bus_id"]

        bus_data = {
            "id": bus_id,
            "bus_number": bus_assignment["bus_number"],
            "registration_number": bus_assignment["registration_number"],
            "capacity": bus_assignment["capacity"],
            "status": bus_assignment["bus_status"]
        }

        # ----------------------------------------------------
        # 3. GET BUS'S LATEST ACTIVE ROUTE ASSIGNMENT
        # ----------------------------------------------------

        route_assignment = connection.execute(
            """
            SELECT
                id,
                route_id,
                assigned_from,
                assigned_until,
                is_active

            FROM bus_route_assignments

            WHERE bus_id = ?
              AND is_active = 1

            ORDER BY id DESC
            LIMIT 1
            """,
            (bus_id,)
        ).fetchone()

        route_data = None
        stops_data = []

        route_assignment_data = None

        # ----------------------------------------------------
        # 4. GET ROUTE DETAILS
        # ----------------------------------------------------

        if route_assignment:

            route_assignment_data = {
                "id": route_assignment["id"],
                "route_id": route_assignment["route_id"],
                "assigned_from": route_assignment["assigned_from"],
                "assigned_until": route_assignment["assigned_until"],
                "is_active": bool(route_assignment["is_active"])
            }

            route = connection.execute(
                """
                SELECT
                    id,
                    route_name,
                    route_code,
                    is_active

                FROM routes

                WHERE id = ?
                  AND is_active = 1

                LIMIT 1
                """,
                (route_assignment["route_id"],)
            ).fetchone()

            if route:

                route_data = {
                    "id": route["id"],
                    "route_name": route["route_name"],
                    "route_code": route["route_code"]
                }

                # ------------------------------------------------
                # 5. GET ACTIVE ROUTE STOPS
                # ------------------------------------------------

                stops = connection.execute(
                    """
                    SELECT
                        id,
                        route_id,
                        stop_name,
                        stop_type,
                        latitude,
                        longitude,
                        stop_order,
                        scheduled_pickup_time,
                        scheduled_drop_time

                    FROM stops

                    WHERE route_id = ?
                      AND is_active = 1

                    ORDER BY stop_order ASC, id ASC
                    """,
                    (route["id"],)
                ).fetchall()

                stops_data = [
                    dict(stop)
                    for stop in stops
                ]

        # ----------------------------------------------------
        # 6. RETURN COMPLETE DRIVER ASSIGNMENT
        # ----------------------------------------------------

        connection.commit()

        return jsonify({

            "success": True,

            "driver": driver_data,

            "bus": bus_data,

            "route": route_data,

            "stops": stops_data,

            "has_active_route": route_data is not None,

            "assignment": {

                "id": bus_assignment["assignment_id"],

                "assigned_from": bus_assignment["assigned_from"],

                "assigned_until": bus_assignment["assigned_until"],

                "is_active": bool(
                    bus_assignment["assignment_is_active"]
                ),

                "route_assignment": route_assignment_data
            },

            "assignment_api_version": "2026-11-02-v2"

        }), 200

    except Exception as error:

        connection.rollback()

        print(
            "Driver assignment API error:",
            repr(error)
        )

        return jsonify({

            "success": False,

            "message": "Unable to load driver assignment.",

            "error": str(error),

            "assignment_api_version": "2026-11-02-v2"

        }), 500

    finally:

        connection.close()