from flask import Blueprint, request, jsonify
from database import get_connection
from auth import role_required

route_bp = Blueprint("route", __name__, url_prefix="/api/routes")


@route_bp.post("")
@role_required("ADMIN")
def create_route():
    data = request.get_json(silent=True) or {}

    route_name = str(data.get("route_name", "")).strip()
    route_code = str(data.get("route_code", "")).strip().upper()
    description = str(data.get("description", "")).strip() or None

    if not route_name:
        return jsonify({"success": False, "message": "Route name is required."}), 400

    connection = get_connection()
    try:
        cursor = connection.execute(
            "INSERT INTO routes (route_name, route_code, description) VALUES (?, ?, ?)",
            (route_name, route_code or None, description),
        )
        route_id = cursor.lastrowid

        # Keep legacy clients working while ensuring every new route gets a code.
        if not route_code:
            route_code = f"ROUTE-{route_id}"
            connection.execute(
                "UPDATE routes SET route_code = ? WHERE id = ?",
                (route_code, route_id),
            )

        connection.commit()
        return jsonify({
            "success": True,
            "message": "Route created successfully.",
            "id": route_id,
            "route_id": route_id,
            "route": {"id": route_id, "route_name": route_name, "route_code": route_code, "description": description},
        }), 201

    except Exception as error:
        connection.rollback()
        message = str(error)
        status = 409 if "UNIQUE constraint failed" in message else 500
        return jsonify({
            "success": False,
            "message": "Route code already exists." if status == 409 else "Failed to create route.",
            "error": message,
        }), status
    finally:
        connection.close()
