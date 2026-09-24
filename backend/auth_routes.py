import uuid
from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash

from config import Config
from database import get_connection


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)


@auth_bp.post("/login")
def login():

    data = request.get_json() or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    connection = get_connection()

    try:

        user = connection.execute("""
            SELECT
                id,
                username,
                password_hash,
                role,
                is_active
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Invalid username or password"
            }), 401

        if not user["is_active"]:
            return jsonify({
                "success": False,
                "message": "User account is inactive"
            }), 403

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid username or password"
            }), 401

        jti = str(uuid.uuid4())

        now = datetime.now(timezone.utc)

        payload = {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(hours=8)
        }

        token = jwt.encode(
            payload,
            Config.SECRET_KEY,
            algorithm="HS256"
        )

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"]
            }
        }), 200

    except Exception as error:

        print("Login error:", error)

        return jsonify({
            "success": False,
            "message": "Unable to login",
            "error": str(error)
        }), 500

    finally:
        connection.close()