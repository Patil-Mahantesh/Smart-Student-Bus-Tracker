import jwt
import sqlite3
from functools import wraps
from flask import request, jsonify, g
from config import Config
from database import get_connection

JWT_SECRET_KEY = Config.SECRET_KEY

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "message": "Authorization token is required"
            }), 401

        parts = auth_header.split(" ")

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({
                "message": "Invalid authorization header"
            }), 401

        token = parts[1]

        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=["HS256"]
            )

            connection = get_connection()
            user = connection.execute(
                "SELECT id, role, is_active FROM users WHERE id = ?",
                (payload.get("user_id"),),
            ).fetchone()
            revoked = connection.execute(
                "SELECT 1 FROM revoked_tokens WHERE jti = ?",
                (payload.get("jti"),),
            ).fetchone() if payload.get("jti") else None
            connection.close()

            if not user or not user["is_active"]:
                return jsonify({
                    "success": False,
                    "error": "Unauthenticated",
                    "code": "UNAUTHENTICATED",
                }), 401

            if revoked:
                return jsonify({
                    "success": False,
                    "error": "Unauthenticated",
                    "code": "TOKEN_REVOKED",
                }), 401

            g.user = payload

        except jwt.ExpiredSignatureError:
            return jsonify({
                "message": "Token has expired"
            }), 401

        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "error": "Unauthenticated",
                "code": "INVALID_TOKEN",
            }), 401

        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    def decorator(function):
        @wraps(function)
        @token_required
        def decorated(*args, **kwargs):
            if g.user.get("role") not in roles:
                return jsonify({
                    "success": False,
                    "error": "You do not have permission to perform this action",
                    "code": "FORBIDDEN",
                }), 403
            return function(*args, **kwargs)

        return decorated

    return decorator