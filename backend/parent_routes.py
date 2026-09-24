from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash

from database import get_connection
from auth import role_required


parent_bp = Blueprint(
    "parent",
    __name__,
    url_prefix="/api/parents"
)


# ============================================================
# ADMIN - CREATE PARENT
# ============================================================

@parent_bp.post("")
@role_required("ADMIN")
def create_parent():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()

    if not username or not password or not name:
        return jsonify({
            "status": "error",
            "message": "username, password and name are required"
        }), 400

    connection = get_connection()

    existing_user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing_user:
        connection.close()

        return jsonify({
            "status": "error",
            "message": "Username already exists"
        }), 409

    try:
        password_hash = generate_password_hash(password)

        cursor = connection.execute(
            """
            INSERT INTO users
            (username, password_hash, role)
            VALUES (?, ?, 'PARENT')
            """,
            (username, password_hash)
        )

        user_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO parents
            (user_id, name, phone, email)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, phone, email)
        )

        parent_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "status": "ok",
            "message": "Parent created successfully",
            "parent": {
                "id": parent_id,
                "user_id": user_id,
                "username": username,
                "name": name
            }
        }), 201

    except Exception:
        connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to create parent"
        }), 500

    finally:
        connection.close()


# ============================================================
# PARENT - CURRENT PROFILE
# ============================================================

@parent_bp.get("/me")
@role_required("PARENT")
def get_my_profile():
    connection = get_connection()

    try:
        parent = connection.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.name,
                p.father_name,
                p.mother_name,
                p.phone,
                p.email,
                u.username,
                u.is_active
            FROM parents p
            JOIN users u ON u.id = p.user_id
            WHERE p.user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not parent:
            return jsonify({
                "status": "error",
                "message": "Parent profile not found"
            }), 404

        return jsonify({
            "status": "ok",
            "parent": dict(parent)
        }), 200

    finally:
        connection.close()


# ============================================================
# PARENT - MY CHILDREN
# ============================================================

@parent_bp.get("/children")
@role_required("PARENT")
def get_my_children():
    """
    Return only the students linked to the currently logged-in
    parent account.

    This removes the old hard-coded student_id=1 behavior.
    """

    connection = get_connection()

    try:
        parent = connection.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.name,
                p.father_name,
                p.mother_name,
                p.phone,
                p.email,
                u.username
            FROM parents p
            JOIN users u ON u.id = p.user_id
            WHERE p.user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not parent:
            return jsonify({
                "status": "error",
                "message": "Parent profile not found"
            }), 404

        rows = connection.execute(
            """
            SELECT
                s.id,
                s.student_code,
                s.name,
                s.class_name,
                s.pickup_stop_id,
                s.drop_stop_id,
                s.bus_id,
                s.status,
                s.is_active,
                s.created_at,

                b.bus_number,
                b.registration_number,
                b.capacity,
                b.status AS bus_status,

                pickup.stop_name AS pickup_stop_name,
                pickup.latitude AS pickup_latitude,
                pickup.longitude AS pickup_longitude,

                dropoff.stop_name AS drop_stop_name,
                dropoff.latitude AS drop_latitude,
                dropoff.longitude AS drop_longitude

            FROM student_parents sp

            JOIN students s
                ON s.id = sp.student_id

            LEFT JOIN buses b
                ON b.id = s.bus_id

            LEFT JOIN stops pickup
                ON pickup.id = s.pickup_stop_id

            LEFT JOIN stops dropoff
                ON dropoff.id = s.drop_stop_id

            WHERE sp.parent_id = ?

            ORDER BY s.name COLLATE NOCASE ASC
            """,
            (parent["id"],)
        ).fetchall()

        children = []

        for row in rows:
            child = dict(row)

            child["bus"] = None

            if child["bus_id"] is not None:
                child["bus"] = {
                    "id": child["bus_id"],
                    "bus_number": child["bus_number"],
                    "registration_number": child["registration_number"],
                    "capacity": child["capacity"],
                    "status": child["bus_status"]
                }

            child["pickup_stop"] = None

            if child["pickup_stop_id"] is not None:
                child["pickup_stop"] = {
                    "id": child["pickup_stop_id"],
                    "name": child["pickup_stop_name"],
                    "latitude": child["pickup_latitude"],
                    "longitude": child["pickup_longitude"]
                }

            child["drop_stop"] = None

            if child["drop_stop_id"] is not None:
                child["drop_stop"] = {
                    "id": child["drop_stop_id"],
                    "name": child["drop_stop_name"],
                    "latitude": child["drop_latitude"],
                    "longitude": child["drop_longitude"]
                }

            # Remove flattened fields that are already represented
            # by the nested objects.
            for key in (
                "bus_number",
                "registration_number",
                "capacity",
                "bus_status",
                "pickup_stop_name",
                "pickup_latitude",
                "pickup_longitude",
                "drop_stop_name",
                "drop_latitude",
                "drop_longitude"
            ):
                child.pop(key, None)

            children.append(child)

        return jsonify({
            "status": "ok",
            "parent": {
                "id": parent["id"],
                "user_id": parent["user_id"],
                "username": parent["username"],
                "name": parent["name"],
                "father_name": parent["father_name"],
                "mother_name": parent["mother_name"],
                "phone": parent["phone"],
                "email": parent["email"]
            },
            "children": children,
            "count": len(children)
        }), 200

    finally:
        connection.close()
