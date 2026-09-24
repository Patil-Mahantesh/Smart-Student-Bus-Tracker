from auth import role_required, token_required
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash
from database import get_connection

driver_bp = Blueprint("driver", __name__, url_prefix="/api/drivers")


@driver_bp.post("")
@role_required("ADMIN")
def create_driver():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")
    name = data.get("name")
    phone = data.get("phone")
    license_number = data.get("license_number")

    if not username or not password or not name:
        return jsonify({
            "message": "username, password and name are required"
        }), 400

    connection = get_connection()

    try:
        password_hash = generate_password_hash(password)

        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, "DRIVER")
        )

        user_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO drivers
            (user_id, name, phone, license_number)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, phone, license_number)
        )

        driver_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "message": "Driver created successfully",
            "driver_id": driver_id
        }), 201

    except Exception as error:
        connection.rollback()

        return jsonify({
            "message": "Could not create driver",
            "error": str(error)
        }), 409

    finally:
        connection.close()


@driver_bp.get("/assignment")
@token_required
def get_driver_assignment():
    connection = get_connection()

    try:
        user_id = g.user["user_id"]

        driver = connection.execute(
            "SELECT id FROM drivers WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not driver:
            return jsonify({
                "message": "Driver profile not found"
            }), 404

        driver_id = driver["id"]
        result = connection.execute(
            """
            SELECT
                d.id AS driver_id,
                d.name AS driver_name,
                d.phone,
                d.license_number,
                b.id AS bus_id,
                b.bus_number,
                b.registration_number,
                b.capacity,
                b.status AS bus_status,
                a.assigned_from,
                a.assigned_until,
                a.is_active
            FROM driver_bus_assignments a
            JOIN drivers d ON d.id = a.driver_id
            JOIN buses b ON b.id = a.bus_id
            WHERE a.driver_id = ?
              AND a.is_active = 1
            ORDER BY a.id DESC
            LIMIT 1
            """,
            (driver_id,)
        ).fetchone()

        if not result:
            return jsonify({
                "message": "No active bus assignment found"
            }), 404

        return jsonify({
            "driver": {
                "id": result["driver_id"],
                "name": result["driver_name"],
                "phone": result["phone"],
                "license_number": result["license_number"]
            },
            "bus": {
                "id": result["bus_id"],
                "bus_number": result["bus_number"],
                "registration_number": result["registration_number"],
                "capacity": result["capacity"],
                "status": result["bus_status"]
            },
            "assignment": {
                "assigned_from": result["assigned_from"],
                "assigned_until": result["assigned_until"],
                "is_active": result["is_active"]
            }
        }), 200

    finally:
        connection.close()