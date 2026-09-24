from flask import Blueprint, request, jsonify
from database import get_connection
from auth import role_required

bus_bp = Blueprint("bus", __name__, url_prefix="/api/buses")


@bus_bp.post("")
@role_required("ADMIN")
def create_bus():
    data = request.get_json()

    bus_number = data.get("bus_number")
    registration_number = data.get("registration_number")
    capacity = data.get("capacity")
    status = data.get("status", "ACTIVE")

    if not bus_number:
        return jsonify({
            "message": "bus_number is required"
        }), 400

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO buses
            (bus_number, registration_number, capacity, status)
            VALUES (?, ?, ?, ?)
            """,
            (bus_number, registration_number, capacity, status)
        )

        bus_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Bus created successfully",
            "bus_id": bus_id
        }), 201

    except Exception as error:
        connection.rollback()

        return jsonify({
            "message": "Could not create bus",
            "error": str(error)
        }), 409

    finally:
        connection.close()


@bus_bp.post("/<int:bus_id>/assign-driver")
@role_required("ADMIN")
def assign_driver(bus_id):
    data = request.get_json()

    driver_id = data.get("driver_id")

    if not driver_id:
        return jsonify({
            "message": "driver_id is required"
        }), 400

    connection = get_connection()

    try:
        bus = connection.execute(
            "SELECT id FROM buses WHERE id = ?",
            (bus_id,)
        ).fetchone()

        if not bus:
            return jsonify({
                "message": "Bus not found"
            }), 404

        driver = connection.execute(
            "SELECT id FROM drivers WHERE id = ?",
            (driver_id,)
        ).fetchone()

        if not driver:
            return jsonify({
                "message": "Driver not found"
            }), 404

        connection.execute(
            """
            UPDATE driver_bus_assignments
            SET is_active = 0,
                assigned_until = CURRENT_TIMESTAMP
            WHERE driver_id = ? AND is_active = 1
            """,
            (driver_id,)
        )

        cursor = connection.execute(
            """
            INSERT INTO driver_bus_assignments
            (driver_id, bus_id, assigned_from, is_active)
            VALUES (?, ?, CURRENT_TIMESTAMP, 1)
            """,
            (driver_id, bus_id)
        )

        assignment_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "message": "Driver assigned to bus successfully",
            "assignment_id": assignment_id,
            "driver_id": driver_id,
            "bus_id": bus_id
        }), 201

    except Exception as error:
        connection.rollback()

        return jsonify({
            "message": "Could not assign driver",
            "error": str(error)
        }), 409

    finally:
        connection.close()