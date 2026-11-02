from flask import Blueprint, request, jsonify, g
from database import get_connection
from auth import role_required


travel_bp = Blueprint(
    "travel",
    __name__,
    url_prefix="/api/travel"
)


# ============================================================
# UPDATE TRAVEL STATUS
# Parent: COMING / NOT_COMING
# ============================================================

@travel_bp.post("/status")
@role_required("PARENT")
def update_travel_status():

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    status = data.get("status")
    travel_date = data.get("travel_date")

    if not student_id or not status or not travel_date:
        return jsonify({
            "success": False,
            "message": "student_id, status and travel_date are required"
        }), 400

    if status not in ("COMING", "NOT_COMING"):
        return jsonify({
            "success": False,
            "message": "Invalid travel status"
        }), 400

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # Check student
        # ----------------------------------------------------

        student = connection.execute(
            """
            SELECT
                id,
                name,
                is_active
            FROM students
            WHERE id = ?
            """,
            (student_id,)
        ).fetchone()

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


        # ----------------------------------------------------
        # Get logged-in parent
        # ----------------------------------------------------

        parent = connection.execute(
            """
            SELECT id
            FROM parents
            WHERE user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not parent:
            return jsonify({
                "success": False,
                "message": "Parent profile not found"
            }), 404


        # ----------------------------------------------------
        # Verify parent -> student relationship
        # ----------------------------------------------------

        linked = connection.execute(
            """
            SELECT 1
            FROM student_parents
            WHERE student_id = ?
              AND parent_id = ?
            """,
            (
                student_id,
                parent["id"]
            )
        ).fetchone()

        if not linked:
            return jsonify({
                "success": False,
                "message": "You are not authorized for this student"
            }), 403


        # ----------------------------------------------------
        # Insert or update today's status
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO travel_status
            (
                student_id,
                status,
                travel_date
            )
            VALUES (?, ?, ?)

            ON CONFLICT(student_id, travel_date)
            DO UPDATE SET
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                student_id,
                status,
                travel_date
            )
        )

        connection.commit()


        return jsonify({
            "success": True,
            "message": "Travel status updated successfully",
            "student_id": student_id,
            "student_name": student["name"],
            "status": status,
            "travel_date": travel_date
        }), 200


    except Exception as error:

        connection.rollback()

        print(
            "Travel status update error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Failed to update travel status"
        }), 500

    finally:
        connection.close()


# ============================================================
# GET ONE STUDENT'S TRAVEL STATUS
# Parent
# ============================================================

@travel_bp.get("/status/<int:student_id>")
@role_required("PARENT")
def get_travel_status(student_id):

    travel_date = request.args.get("travel_date")

    if not travel_date:
        return jsonify({
            "success": False,
            "message": "travel_date is required"
        }), 400

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # Verify parent
        # ----------------------------------------------------

        parent = connection.execute(
            """
            SELECT id
            FROM parents
            WHERE user_id = ?
            """,
            (g.user["user_id"],)
        ).fetchone()

        if not parent:
            return jsonify({
                "success": False,
                "message": "Parent profile not found"
            }), 404


        # ----------------------------------------------------
        # Verify parent owns student
        # ----------------------------------------------------

        linked = connection.execute(
            """
            SELECT 1
            FROM student_parents
            WHERE student_id = ?
              AND parent_id = ?
            """,
            (
                student_id,
                parent["id"]
            )
        ).fetchone()

        if not linked:
            return jsonify({
                "success": False,
                "message": "You are not authorized for this student"
            }), 403


        # ----------------------------------------------------
        # Get status
        # ----------------------------------------------------

        status = connection.execute(
            """
            SELECT
                ts.student_id,
                s.name AS student_name,
                ts.status,
                ts.travel_date,
                ts.updated_at
            FROM travel_status ts

            INNER JOIN students s
                ON s.id = ts.student_id

            WHERE ts.student_id = ?
              AND ts.travel_date = ?
            """,
            (
                student_id,
                travel_date
            )
        ).fetchone()


        # ----------------------------------------------------
        # DEFAULT = COMING
        # ----------------------------------------------------

        if not status:

            return jsonify({
                "success": True,
                "student_id": student_id,
                "status": "COMING",
                "travel_date": travel_date,
                "updated_at": None
            }), 200


        return jsonify({
            "success": True,
            "student_id": status["student_id"],
            "student_name": status["student_name"],
            "status": status["status"] or "COMING",
            "travel_date": status["travel_date"],
            "updated_at": status["updated_at"]
        }), 200


    except Exception as error:

        print(
            "Travel status fetch error:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Failed to fetch travel status"
        }), 500

    finally:
        connection.close()


# ============================================================
# GET TODAY'S STUDENT TRAVEL STATUS
# Driver
# ============================================================

@travel_bp.get("/today")
@role_required("DRIVER")
def get_today_travel_status():
    travel_date = request.args.get("travel_date")
    if not travel_date:
        return jsonify({
            "success": False,
            "message": "travel_date is required"
        }), 400

    connection = get_connection()
    try:
        driver = connection.execute(
            "SELECT id FROM drivers WHERE user_id = ?",
            (g.user["user_id"],)
        ).fetchone()
        if not driver:
            return jsonify({"success": False, "message": "Driver profile not found"}), 404

        assignment = connection.execute(
            """
            SELECT bus_id FROM driver_bus_assignments
            WHERE driver_id = ? AND is_active = 1
            ORDER BY id DESC LIMIT 1
            """,
            (driver["id"],)
        ).fetchone()
        if not assignment:
            return jsonify({
                "success": False,
                "message": "No active bus is assigned to this driver. Contact Admin."
            }), 409

        rows = connection.execute(
            """
            SELECT
                s.id AS student_id,
                s.student_code,
                s.name AS student_name,
                COALESCE(ts.status, 'COMING') AS status,
                ts.travel_date,
                ts.updated_at,
                CASE WHEN COALESCE(att.picked_up, 0) = 1 THEN 'PICKED_UP' ELSE 'WAITING' END AS pickup_status,
                CASE WHEN COALESCE(att.dropped_off, 0) = 1 THEN 'DROPPED_OFF' ELSE 'WAITING' END AS drop_status
            FROM students s
            LEFT JOIN travel_status ts
                ON ts.student_id = s.id AND ts.travel_date = ?
            LEFT JOIN (
                SELECT
                    a.student_id,
                    MAX(CASE WHEN a.attendance_type = 'PICKUP' AND a.status = 'PRESENT' THEN 1 ELSE 0 END) AS picked_up,
                    MAX(CASE WHEN a.attendance_type = 'DROP' AND a.status = 'PRESENT' THEN 1 ELSE 0 END) AS dropped_off
                FROM attendance a
                JOIN trips t ON t.id = a.trip_id
                WHERE a.attendance_date = ? AND t.driver_id = ?
                GROUP BY a.student_id
            ) att ON att.student_id = s.id
            WHERE s.is_active = 1 AND s.bus_id = ?
            ORDER BY s.name COLLATE NOCASE ASC
            """,
            (travel_date, travel_date, driver["id"], assignment["bus_id"])
        ).fetchall()

        students = [{
            "student_id": row["student_id"],
            "student_code": row["student_code"],
            "student_name": row["student_name"],
            "status": row["status"] or "COMING",
            "travel_date": row["travel_date"] or travel_date,
            "updated_at": row["updated_at"],
            "pickup_status": row["pickup_status"],
            "drop_status": row["drop_status"]
        } for row in rows]

        return jsonify({
            "success": True,
            "travel_date": travel_date,
            "bus_id": assignment["bus_id"],
            "students": students,
            "total_students": len(students)
        }), 200

    except Exception as error:
        connection.rollback()
        print("Today's travel status error:", error)
        return jsonify({
            "success": False,
            "message": "Unable to load today's bus students",
            "error": str(error)
        }), 500
    finally:
        connection.close()
