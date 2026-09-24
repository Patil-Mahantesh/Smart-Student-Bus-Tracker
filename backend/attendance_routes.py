from flask import Blueprint, request, jsonify, g
from auth import token_required
from database import get_connection
from datetime import datetime


attendance_bp = Blueprint(
    "attendance",
    __name__,
    url_prefix="/api/attendance"
)


# =========================================================
# MARK ATTENDANCE
# =========================================================

@attendance_bp.post("/mark")
@token_required
def mark_attendance():

    data = request.get_json() or {}

    student_id = data.get("student_id")
    confidence = data.get("confidence")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not student_id:
        return jsonify({
            "success": False,
            "message": "student_id is required"
        }), 400

    connection = get_connection()

    try:

        # -------------------------------------------------
        # 1. Find logged-in driver
        # -------------------------------------------------

        driver = connection.execute("""
            SELECT
                id,
                name
            FROM drivers
            WHERE user_id = ?
        """, (
            g.user["user_id"],
        )).fetchone()

        if not driver:
            return jsonify({
                "success": False,
                "message": "Driver profile not found"
            }), 404


        # -------------------------------------------------
        # 2. Find driver's active trip
        # -------------------------------------------------

        trip = connection.execute("""
            SELECT
                id,
                bus_id,
                route_id,
                trip_type,
                status
            FROM trips
            WHERE driver_id = ?
              AND status = 'IN_PROGRESS'
            ORDER BY id DESC
            LIMIT 1
        """, (
            driver["id"],
        )).fetchone()

        if not trip:
            return jsonify({
                "success": False,
                "message": (
                    "No active trip found. "
                    "Please start a trip first."
                )
            }), 400


        # -------------------------------------------------
        # 3. Find student
        # -------------------------------------------------

        student = connection.execute("""
            SELECT
                id,
                student_code,
                name,
                is_active
            FROM students
            WHERE id = ?
        """, (
            student_id,
        )).fetchone()

        if not student:
            return jsonify({
                "success": False,
                "message": "Student not found"
            }), 404


        if not student["is_active"]:
            return jsonify({
                "success": False,
                "message": "Student is inactive"
            }), 400


        # -------------------------------------------------
        # 4. Check today's travel status
        # -------------------------------------------------

        travel_status = connection.execute("""
            SELECT
                status
            FROM travel_status
            WHERE student_id = ?
              AND travel_date = DATE('now')
        """, (
            student_id,
        )).fetchone()


        if (
            travel_status
            and travel_status["status"] == "NOT_COMING"
        ):

            return jsonify({
                "success": False,
                "message": (
                    f"{student['name']} is marked as "
                    "NOT COMING today. "
                    "Attendance cannot be recorded."
                )
            }), 400


        # -------------------------------------------------
        # 5. Determine attendance type
        # -------------------------------------------------

        if trip["trip_type"] == "PICKUP":

            attendance_type = "PICKUP"

        elif trip["trip_type"] == "DROP":

            attendance_type = "DROP"

        else:

            return jsonify({
                "success": False,
                "message": "Invalid trip type"
            }), 400


        # -------------------------------------------------
        # 6. Prevent duplicate attendance
        # -------------------------------------------------

        existing = connection.execute("""
            SELECT
                id,
                status,
                attendance_date,
                recognized_at,
                recorded_at
            FROM attendance
            WHERE trip_id = ?
              AND student_id = ?
              AND attendance_type = ?
        """, (
            trip["id"],
            student_id,
            attendance_type
        )).fetchone()


        if existing:

            return jsonify({

                "success": True,

                "already_marked": True,

                "message": (
                    f"{student['name']} "
                    "attendance already marked"
                ),

                "attendance": {

                    "id": existing["id"],

                    "student_id": student["id"],

                    "student_code":
                        student["student_code"],

                    "student_name":
                        student["name"],

                    "trip_id":
                        trip["id"],

                    "trip_type":
                        trip["trip_type"],

                    "attendance_type":
                        attendance_type,

                    "status":
                        existing["status"],

                    "attendance_date":
                        existing["attendance_date"],

                    "recognized_at":
                        existing["recognized_at"],

                    "recorded_at":
                        existing["recorded_at"]
                }

            }), 200


        # -------------------------------------------------
        # 7. Record attendance
        # -------------------------------------------------

        recognized_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        attendance_date = datetime.now().strftime(
            "%Y-%m-%d"
        )


        cursor = connection.execute("""
            INSERT INTO attendance
            (
                trip_id,
                student_id,
                attendance_type,
                status,
                attendance_date,
                recognized_at,
                recorded_by,
                method,
                latitude,
                longitude,
                confidence
            )
            VALUES (
                ?,
                ?,
                ?,
                'PRESENT',
                ?,
                ?,
                ?,
                'FACE_RECOGNITION',
                ?,
                ?,
                ?
            )
        """, (
            trip["id"],
            student_id,
            attendance_type,
            attendance_date,
            recognized_at,
            g.user["user_id"],
            latitude,
            longitude,
            confidence
        ))


        attendance_id = cursor.lastrowid


        # -------------------------------------------------
        # 8. Find parents
        # -------------------------------------------------

        parents = connection.execute("""
            SELECT
                p.id AS parent_id,
                p.user_id,
                p.name
            FROM student_parents sp
            INNER JOIN parents p
                ON p.id = sp.parent_id
            WHERE sp.student_id = ?
        """, (
            student_id,
        )).fetchall()


        # -------------------------------------------------
        # 9. Create parent notifications
        # -------------------------------------------------

        if attendance_type == "PICKUP":

            notification_title = (
                "Bus Pickup Attendance"
            )

            notification_message = (
                f"{student['name']} has boarded "
                "the bus successfully. "
                "Pickup attendance recorded at "
                f"{datetime.now().strftime('%I:%M %p')}."
            )

        else:

            notification_title = (
                "Bus Drop Attendance"
            )

            notification_message = (
                f"{student['name']} has reached "
                "the drop location. "
                "Drop attendance recorded at "
                f"{datetime.now().strftime('%I:%M %p')}."
            )


        for parent in parents:

            connection.execute("""
                INSERT INTO notifications
                (
                    parent_id,
                    student_id,
                    trip_id,
                    type,
                    title,
                    message,
                    is_read
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    0
                )
            """, (
                parent["parent_id"],
                student_id,
                trip["id"],
                attendance_type,
                notification_title,
                notification_message
            ))


        # -------------------------------------------------
        # 10. Save everything
        # -------------------------------------------------

        connection.commit()


        # -------------------------------------------------
        # 11. Return response
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "already_marked": False,

            "message": (
                f"{student['name']} marked PRESENT"
            ),

            "notification_created":
                len(parents) > 0,

            "notification_count":
                len(parents),

            "attendance": {

                "id":
                    attendance_id,

                "student_id":
                    student["id"],

                "student_code":
                    student["student_code"],

                "student_name":
                    student["name"],

                "trip_id":
                    trip["id"],

                "trip_type":
                    trip["trip_type"],

                "attendance_type":
                    attendance_type,

                "status":
                    "PRESENT",

                "attendance_date":
                    attendance_date,

                "recognized_at":
                    recognized_at,

                "recorded_at":
                    recognized_at,

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "confidence":
                    confidence
            }

        }), 201


    except Exception as error:

        connection.rollback()

        print(
            "Attendance error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to mark attendance",

            "error":
                str(error)

        }), 500


    finally:

        connection.close()


# =========================================================
# GET STUDENT ATTENDANCE HISTORY
# =========================================================

@attendance_bp.get(
    "/student/<int:student_id>"
)
@token_required
def get_student_attendance(student_id):

    connection = get_connection()

    try:

        records = connection.execute("""
            SELECT
                id,
                student_id,
                trip_id,
                attendance_type,
                status,
                attendance_date,
                recognized_at,
                recorded_at,
                recorded_by,
                method,
                latitude,
                longitude,
                confidence
            FROM attendance
            WHERE student_id = ?
            ORDER BY
                attendance_date DESC,
                recognized_at DESC,
                recorded_at DESC
        """, (
            student_id,
        )).fetchall()


        attendance = []


        for record in records:

            attendance.append({

                "id":
                    record["id"],

                "student_id":
                    record["student_id"],

                "trip_id":
                    record["trip_id"],

                "attendance_type":
                    record["attendance_type"],

                "status":
                    record["status"],

                "attendance_date":
                    record["attendance_date"],

                "recognized_at":
                    record["recognized_at"],

                "recorded_at":
                    record["recorded_at"],

                "recorded_by":
                    record["recorded_by"],

                "method":
                    record["method"],

                "latitude":
                    record["latitude"],

                "longitude":
                    record["longitude"],

                "confidence":
                    record["confidence"]
            })


        return jsonify({

            "success": True,

            "student_id":
                student_id,

            "attendance":
                attendance

        }), 200


    except Exception as error:

        print(
            "Attendance history error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "Unable to fetch attendance history",

            "error":
                str(error)

        }), 500


    finally:

        connection.close()