from datetime import date, datetime

from flask import Blueprint, g, jsonify, request

from auth import role_required
from database import get_connection


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _row_dicts(rows):
    return [dict(row) for row in rows]


# ============================================================
# ADMIN OVERVIEW
# ============================================================

@admin_bp.get("/overview")
@role_required("ADMIN")
def get_overview():
    connection = get_connection()

    try:
        counts = {
            "students": connection.execute(
                "SELECT COUNT(*) FROM students WHERE is_active = 1"
            ).fetchone()[0],

            "buses": connection.execute(
                "SELECT COUNT(*) FROM buses WHERE is_active = 1"
            ).fetchone()[0],

            "drivers": connection.execute(
                """
                SELECT COUNT(*)
                FROM drivers d
                JOIN users u ON u.id = d.user_id
                WHERE d.is_active = 1 AND u.is_active = 1
                """
            ).fetchone()[0],

            "parents": connection.execute(
                """
                SELECT COUNT(*)
                FROM parents p
                JOIN users u ON u.id = p.user_id
                WHERE u.is_active = 1
                """
            ).fetchone()[0],

            "routes": connection.execute(
                "SELECT COUNT(*) FROM routes WHERE is_active = 1"
            ).fetchone()[0],

            "stops": connection.execute(
                "SELECT COUNT(*) FROM stops WHERE is_active = 1"
            ).fetchone()[0],

            "active_trips": connection.execute(
                """
                SELECT COUNT(*)
                FROM trips
                WHERE status = 'IN_PROGRESS'
                """
            ).fetchone()[0],
        }

        return jsonify({
            "success": True,
            "counts": counts,
        }), 200

    finally:
        connection.close()


# ============================================================
# BUS MANAGEMENT
# ============================================================

@admin_bp.get("/buses")
@role_required("ADMIN")
def get_buses():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                b.id,
                b.bus_number,
                b.registration_number,
                b.capacity,
                b.status,
                b.is_active,
                b.created_at,

                d.id AS driver_id,
                d.name AS driver_name,
                d.phone AS driver_phone,

                r.id AS route_id,
                r.route_name,
                r.route_code,

                (SELECT t.id FROM trips t
                 WHERE t.bus_id = b.id AND t.status = 'IN_PROGRESS'
                 ORDER BY t.id DESC LIMIT 1) AS active_trip_id,
                (SELECT t.trip_type FROM trips t
                 WHERE t.bus_id = b.id AND t.status = 'IN_PROGRESS'
                 ORDER BY t.id DESC LIMIT 1) AS active_trip_type,
                (SELECT bl.latitude FROM bus_locations bl
                 JOIN trips t ON t.id = bl.trip_id
                 WHERE t.bus_id = b.id AND t.status = 'IN_PROGRESS'
                 ORDER BY bl.recorded_at DESC, bl.id DESC LIMIT 1) AS latitude,
                (SELECT bl.longitude FROM bus_locations bl
                 JOIN trips t ON t.id = bl.trip_id
                 WHERE t.bus_id = b.id AND t.status = 'IN_PROGRESS'
                 ORDER BY bl.recorded_at DESC, bl.id DESC LIMIT 1) AS longitude,
                (SELECT bl.recorded_at FROM bus_locations bl
                 JOIN trips t ON t.id = bl.trip_id
                 WHERE t.bus_id = b.id AND t.status = 'IN_PROGRESS'
                 ORDER BY bl.recorded_at DESC, bl.id DESC LIMIT 1) AS recorded_at

            FROM buses b

            LEFT JOIN driver_bus_assignments a
                ON a.bus_id = b.id
                AND a.is_active = 1
                AND a.id = (
                    SELECT MAX(a2.id)
                    FROM driver_bus_assignments a2
                    WHERE a2.bus_id = b.id
                    AND a2.is_active = 1
                )

            LEFT JOIN drivers d
                ON d.id = a.driver_id

            LEFT JOIN (
                SELECT ba.bus_id, ba.route_id
                FROM bus_route_assignments ba
                WHERE ba.is_active = 1
                AND ba.id = (
                    SELECT MAX(ba2.id)
                    FROM bus_route_assignments ba2
                    WHERE ba2.bus_id = ba.bus_id
                    AND ba2.is_active = 1
                )
            ) active_route
                ON active_route.bus_id = b.id

            LEFT JOIN routes r
                ON r.id = active_route.route_id

            WHERE b.is_active = 1

            ORDER BY b.id DESC
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "buses": _row_dicts(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# DRIVER MANAGEMENT
# ============================================================

@admin_bp.get("/drivers")
@role_required("ADMIN")
def get_drivers():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                d.id,
                d.name,
                d.phone,
                d.license_number,
                d.employee_id,
                d.is_active,

                u.username,
                u.is_active AS account_active,

                b.id AS bus_id,
                b.bus_number,

                a.assigned_from

            FROM drivers d

            JOIN users u
                ON u.id = d.user_id

            LEFT JOIN driver_bus_assignments a
                ON a.driver_id = d.id
                AND a.is_active = 1
                AND a.id = (
                    SELECT MAX(a2.id)
                    FROM driver_bus_assignments a2
                    WHERE a2.driver_id = d.id
                    AND a2.is_active = 1
                )

            LEFT JOIN buses b
                ON b.id = a.bus_id

            WHERE d.is_active = 1

            ORDER BY d.id DESC
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "drivers": _row_dicts(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# PARENT MANAGEMENT
# ============================================================

@admin_bp.get("/parents")
@role_required("ADMIN")
def get_parents():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                p.id,
                p.name,
                p.father_name,
                p.mother_name,
                p.phone,
                p.email,
                p.user_id,

                u.username,
                u.is_active AS account_active,
                u.created_at,

                COUNT(DISTINCT sp.student_id) AS child_count

            FROM parents p

            JOIN users u
                ON u.id = p.user_id

            LEFT JOIN student_parents sp
                ON sp.parent_id = p.id

            GROUP BY p.id

            ORDER BY p.id DESC
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "parents": _row_dicts(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# ROUTE MANAGEMENT DATA
# ============================================================

@admin_bp.get("/routes")
@role_required("ADMIN")
def get_routes():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                r.id,
                r.route_name,
                r.route_code,
                r.description,
                r.is_active,

                COUNT(s.id) AS stop_count

            FROM routes r

            LEFT JOIN stops s
                ON s.route_id = r.id
                AND s.is_active = 1

            WHERE r.is_active = 1

            GROUP BY r.id

            ORDER BY r.id DESC
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "routes": _row_dicts(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# ATTENDANCE MANAGEMENT
# ============================================================

@admin_bp.get("/attendance")
@role_required("ADMIN")
def get_attendance():

    requested_date = (
        request.args.get("date") or date.today().isoformat()
    ).strip()

    try:
        datetime.strptime(requested_date, "%Y-%m-%d")

    except ValueError:
        return jsonify({
            "success": False,
            "message": "date must use YYYY-MM-DD format",
        }), 400

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                a.id,
                a.student_id,
                a.attendance_type,
                a.attendance_date,
                a.status,
                a.method,
                a.recognized_at,
                a.recorded_at,
                a.confidence,

                s.student_code,
                s.name AS student_name,
                s.class_name,

                b.bus_number,
                r.route_name,
                d.name AS driver_name

            FROM attendance a

            JOIN students s
                ON s.id = a.student_id

            LEFT JOIN trips t
                ON t.id = a.trip_id

            LEFT JOIN buses b
                ON b.id = t.bus_id

            LEFT JOIN routes r
                ON r.id = t.route_id

            LEFT JOIN drivers d
                ON d.id = t.driver_id

            WHERE DATE(a.attendance_date) = DATE(?)

            ORDER BY
                COALESCE(a.recognized_at, a.recorded_at) DESC,
                a.id DESC
            """,
            (requested_date,),
        ).fetchall()

        return jsonify({
            "success": True,
            "date": requested_date,
            "count": len(rows),
            "attendance": _row_dicts(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# NOTIFICATION MANAGEMENT
# ============================================================

@admin_bp.get("/notifications")
@role_required("ADMIN")
def get_admin_notifications():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                n.id,
                n.type,
                n.title,
                n.message,
                n.is_read,
                n.created_at,
                n.student_id,

                s.name AS student_name,
                s.student_code,

                p.id AS parent_id,
                p.name AS parent_name,

                u.username AS parent_username

            FROM notifications n

            JOIN students s
                ON s.id = n.student_id

            JOIN parents p
                ON p.id = n.parent_id

            JOIN users u
                ON u.id = p.user_id

            ORDER BY
                n.created_at DESC,
                n.id DESC

            LIMIT 300
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "notifications": _row_dicts(rows),
            "count": len(rows),
        }), 200

    finally:
        connection.close()


# ============================================================
# ANNOUNCEMENT MANAGEMENT
# ============================================================

@admin_bp.get("/announcements")
@role_required("ADMIN")
def get_announcements():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                e.id,
                e.title,
                e.description,
                e.event_date,
                e.created_at,

                u.username AS created_by_username

            FROM events e

            LEFT JOIN users u
                ON u.id = e.created_by

            ORDER BY
                e.event_date DESC,
                e.id DESC

            LIMIT 300
            """
        ).fetchall()

        return jsonify({
            "success": True,
            "announcements": _row_dicts(rows),
            "count": len(rows),
        }), 200

    finally:
        connection.close()


@admin_bp.post("/announcements")
@role_required("ADMIN")
def create_announcement():

    data = request.get_json(silent=True) or {}

    title = str(data.get("title") or "").strip()

    message = str(data.get("message") or "").strip()

    event_date = str(
        data.get("event_date")
        or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ).strip()

    if not title or not message:
        return jsonify({
            "success": False,
            "message": (
                "Announcement title and message are required."
            ),
        }), 400

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO events (
                title,
                description,
                event_date,
                created_by
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                title,
                message,
                event_date,
                g.user["user_id"],
            ),
        )

        announcement_id = cursor.lastrowid

        recipients = connection.execute(
            """
            SELECT DISTINCT
                sp.parent_id,
                sp.student_id

            FROM student_parents sp

            JOIN parents p
                ON p.id = sp.parent_id

            JOIN users u
                ON u.id = p.user_id

            JOIN students s
                ON s.id = sp.student_id

            WHERE
                u.is_active = 1
                AND s.is_active = 1
            """
        ).fetchall()

        for recipient in recipients:
            connection.execute(
                """
                INSERT INTO notifications (
                    parent_id,
                    student_id,
                    trip_id,
                    type,
                    title,
                    message,
                    is_read
                )
                VALUES (?, ?, NULL, 'ANNOUNCEMENT', ?, ?, 0)
                """,
                (
                    recipient["parent_id"],
                    recipient["student_id"],
                    title,
                    message,
                ),
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Announcement published successfully.",
            "announcement_id": announcement_id,
            "notification_count": len(recipients),
        }), 201

    except Exception as error:
        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to publish announcement.",
            "error": str(error),
        }), 500

    finally:
        connection.close()


# ============================================================
# ADMIN PROFILE
# ============================================================

@admin_bp.get("/profile")
@role_required("ADMIN")
def get_admin_profile():
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                u.id AS user_id,
                u.username,
                u.role,
                u.is_active,
                u.created_at,

                a.name

            FROM users u

            LEFT JOIN admins a
                ON a.user_id = u.id

            WHERE
                u.id = ?
                AND u.role = 'ADMIN'
            """,
            (g.user["user_id"],),
        ).fetchone()

        if not row:
            return jsonify({
                "success": False,
                "message": "Admin account not found.",
            }), 404

        return jsonify({
            "success": True,
            "profile": dict(row),
        }), 200

    finally:
        connection.close()