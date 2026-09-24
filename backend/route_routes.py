from flask import Blueprint, request, jsonify
from database import get_connection
from auth import role_required

route_bp = Blueprint("route", __name__, url_prefix="/api/routes")


@route_bp.post("")
@role_required("ADMIN")
def create_route():
    data = request.get_json()

    route_name = data.get("route_name")
    description = data.get("description")

    if not route_name:
        return jsonify({
            "message": "Route name is required"
        }), 400

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO routes (route_name, description)
            VALUES (?, ?)
            """,
            (route_name, description)
        )

        connection.commit()

        return jsonify({
            "message": "Route created successfully",
            "route_id": cursor.lastrowid
        }), 201

    except Exception as error:
        connection.rollback()

        return jsonify({
            "message": "Failed to create route",
            "error": str(error)
        }), 500

    finally:
        connection.close()