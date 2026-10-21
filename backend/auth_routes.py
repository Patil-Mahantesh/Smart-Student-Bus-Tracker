
import uuid
import logging
from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash

from config import Config
from database import get_connection


logger = logging.getLogger(__name__)

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if (
        not isinstance(username, str)
        or not username.strip()
        or not isinstance(password, str)
        or not password
    ):
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    connection = None

    try:
        connection = get_connection()

        user = connection.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                role,
                is_active
            FROM users
            WHERE username = ?
            """,
            (username.strip(),)
        ).fetchone()

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

        if not Config.SECRET_KEY:
            logger.error("JWT secret key is not configured")
            return jsonify({
                "success": False,
                "message": "Unable to login",
                "error": "INTERNAL_ERROR"
            }), 500

        now = datetime.now(timezone.utc)

        payload = {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "jti": str(uuid.uuid4()),
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

    except Exception:
        logger.exception("Login request failed")

        return jsonify({
            "success": False,
            "message": "Unable to login",
            "error": "INTERNAL_ERROR"
        }), 500

    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                logger.exception(
                    "Failed to close login database connection"
                )
