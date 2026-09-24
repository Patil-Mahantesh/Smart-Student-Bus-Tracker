from flask import Blueprint, jsonify, g
from auth import token_required
from database import get_connection


notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/api/notifications"
)


@notification_bp.get("")
@token_required
def get_notifications():

    connection = get_connection()

    try:

        # Find the parent account of the logged-in user
        parent = connection.execute("""
            SELECT
                id,
                name
            FROM parents
            WHERE user_id = ?
        """, (g.user["user_id"],)).fetchone()

        if not parent:
            return jsonify({
                "success": False,
                "message": "Parent profile not found"
            }), 404

        # Get notifications for this parent
        rows = connection.execute("""
            SELECT
                n.id,
                n.student_id,
                n.trip_id,
                n.type,
                n.title,
                n.message,
                n.is_read,
                n.created_at,
                s.student_code,
                s.name AS student_name
            FROM notifications n
            INNER JOIN students s
                ON s.id = n.student_id
            WHERE n.parent_id = ?
            ORDER BY n.created_at DESC
        """, (parent["id"],)).fetchall()

        notifications = []

        for row in rows:

            notifications.append({
                "id": row["id"],
                "student_id": row["student_id"],
                "student_code": row["student_code"],
                "student_name": row["student_name"],
                "trip_id": row["trip_id"],
                "type": row["type"],
                "title": row["title"],
                "message": row["message"],
                "is_read": bool(row["is_read"]),
                "created_at": row["created_at"]
            })

        unread_count = sum(
            1 for notification in notifications
            if not notification["is_read"]
        )

        return jsonify({

            "success": True,

            "parent": {
                "id": parent["id"],
                "name": parent["name"]
            },

            "unread_count": unread_count,

            "notifications": notifications

        }), 200

    except Exception as error:

        print(
            "Notification fetch error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to fetch notifications",
            "error": str(error)
        }), 500

    finally:

        connection.close()


@notification_bp.put("/<int:notification_id>/read")
@token_required
def mark_notification_read(notification_id):

    connection = get_connection()

    try:

        # Find parent
        parent = connection.execute("""
            SELECT id
            FROM parents
            WHERE user_id = ?
        """, (g.user["user_id"],)).fetchone()

        if not parent:
            return jsonify({
                "success": False,
                "message": "Parent profile not found"
            }), 404

        # Make sure notification belongs to this parent
        notification = connection.execute("""
            SELECT id
            FROM notifications
            WHERE id = ?
              AND parent_id = ?
        """, (
            notification_id,
            parent["id"]
        )).fetchone()

        if not notification:
            return jsonify({
                "success": False,
                "message": "Notification not found"
            }), 404

        connection.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
        """, (notification_id,))

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Notification marked as read"
        }), 200

    except Exception as error:

        connection.rollback()

        print(
            "Notification read error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Unable to update notification",
            "error": str(error)
        }), 500

    finally:

        connection.close()