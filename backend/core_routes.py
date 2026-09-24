import sqlite3

from flask import Blueprint, g, jsonify, request

from auth import role_required, token_required
from database import get_connection
from domain_service import (
    DomainValidationError,
    create_attendance,
    create_student,
    create_trip,
    driver_id_for_user,
    get_student,
    parent_id_for_user,
    serialize_rows,
    update_student,
    validate_coordinates,
    get_row,
    require_id,
    require_text,
)


core_bp = Blueprint("core", __name__, url_prefix="/api")


def error_response(error):
    if isinstance(error, DomainValidationError):
        return jsonify({"success": False, "error": str(error), "code": error.code}), error.status
    if isinstance(error, sqlite3.IntegrityError):
        return jsonify({"success": False, "error": "The requested value conflicts with existing data", "code": "INTEGRITY_ERROR"}), 409
    return jsonify({"success": False, "error": "Database operation failed", "code": "DATABASE_ERROR"}), 500


def row_response(row):
    return jsonify({"success": True, "data": row})


def rows_response(rows, key):
    return jsonify({"success": True, key: serialize_rows(rows)})


@core_bp.post("/auth/logout")
@token_required
def logout():
    connection = get_connection()
    try:
        if g.user.get("jti"):
            connection.execute(
                "INSERT OR IGNORE INTO revoked_tokens (jti, user_id) VALUES (?, ?)",
                (g.user["jti"], g.user["user_id"]),
            )
            connection.commit()
    finally:
        connection.close()
    return jsonify({"success": True, "message": "Logged out successfully"})


@core_bp.get("/profile")
@token_required
def profile():
    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT id, username, role, is_active, created_at FROM users WHERE id = ?",
            (g.user["user_id"],),
        ).fetchone()
        result = {"user": dict(user)}
        table = {"PARENT": "parents", "DRIVER": "drivers", "ADMIN": "admins"}[g.user["role"]]
        details = connection.execute(
            f"SELECT * FROM {table} WHERE user_id = ?",
            (g.user["user_id"],),
        ).fetchone()
        result["profile"] = dict(details) if details else None
        return jsonify({"success": True, **result})
    finally:
        connection.close()


@core_bp.get("/students/")
@token_required
def get_students():
    connection = get_connection()
    try:
        query = """
            SELECT s.*, b.bus_number, r.id AS route_id, r.route_name, r.route_code,
                   ps.stop_name AS pickup_stop_name, ds.stop_name AS drop_stop_name
            FROM students s
            LEFT JOIN buses b ON b.id = s.bus_id
            LEFT JOIN stops ps ON ps.id = s.pickup_stop_id
            LEFT JOIN stops ds ON ds.id = s.drop_stop_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = s.bus_id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
        """
        params = []
        if g.user["role"] == "PARENT":
            parent_id = parent_id_for_user(connection, g.user["user_id"])
            query += " JOIN student_parents sp ON sp.student_id = s.id WHERE sp.parent_id = ?"
            params.append(parent_id)
        elif g.user["role"] == "DRIVER":
            driver_id = driver_id_for_user(connection, g.user["user_id"])
            query += " JOIN driver_bus_assignments dba ON dba.bus_id = s.bus_id AND dba.driver_id = ? AND dba.is_active = 1"
            params.append(driver_id)
        elif g.user["role"] != "ADMIN":
            return jsonify({"success": False, "error": "Forbidden", "code": "FORBIDDEN"}), 403
        query += " ORDER BY s.name"
        return rows_response(connection.execute(query, params).fetchall(), "students")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/students")
@token_required
def get_students_without_slash():
    return get_students()


@core_bp.get("/students/<int:student_id>")
@token_required
def get_student_detail(student_id):
    connection = get_connection()
    try:
        if g.user["role"] == "PARENT":
            parent_id = parent_id_for_user(connection, g.user["user_id"])
            allowed = connection.execute(
                "SELECT 1 FROM student_parents WHERE student_id = ? AND parent_id = ?",
                (student_id, parent_id),
            ).fetchone()
            if not allowed:
                return jsonify({"success": False, "error": "Resource not found", "code": "NOT_FOUND"}), 404
        elif g.user["role"] == "DRIVER":
            driver_id = driver_id_for_user(connection, g.user["user_id"])
            allowed = connection.execute(
                """
                SELECT 1 FROM students s
                JOIN driver_bus_assignments dba ON dba.bus_id = s.bus_id
                WHERE s.id = ? AND dba.driver_id = ? AND dba.is_active = 1
                """,
                (student_id, driver_id),
            ).fetchone()
            if not allowed:
                return jsonify({"success": False, "error": "Resource not found", "code": "NOT_FOUND"}), 404
        elif g.user["role"] != "ADMIN":
            return jsonify({"success": False, "error": "Forbidden", "code": "FORBIDDEN"}), 403
        return row_response(get_student(connection, student_id))
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.post("/students/")
@role_required("ADMIN")
def post_student():
    try:
        return row_response(create_student(request.get_json(silent=True) or {})), 201
    except Exception as error:
        return error_response(error)


@core_bp.post("/students")
@role_required("ADMIN")
def post_student_without_slash():
    return post_student()


@core_bp.patch("/students/<int:student_id>")
@core_bp.put("/students/<int:student_id>")
@role_required("ADMIN")
def patch_student(student_id):
    try:
        return row_response(update_student(student_id, request.get_json(silent=True) or {}))
    except Exception as error:
        return error_response(error)


@core_bp.get("/parents/me")
@role_required("PARENT")
def parent_profile():
    connection = get_connection()
    try:
        parent_id = parent_id_for_user(connection, g.user["user_id"])
        parent = connection.execute(
            "SELECT p.*, u.username, u.is_active FROM parents p JOIN users u ON u.id = p.user_id WHERE p.id = ?",
            (parent_id,),
        ).fetchone()
        children = connection.execute(
            """
            SELECT s.*, b.bus_number, r.route_name, r.route_code,
                   ps.stop_name AS pickup_stop_name, ds.stop_name AS drop_stop_name
            FROM students s
            JOIN student_parents sp ON sp.student_id = s.id
            LEFT JOIN buses b ON b.id = s.bus_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = s.bus_id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
            LEFT JOIN stops ps ON ps.id = s.pickup_stop_id
            LEFT JOIN stops ds ON ds.id = s.drop_stop_id
            WHERE sp.parent_id = ? ORDER BY s.name
            """,
            (parent_id,),
        ).fetchall()
        return jsonify({"success": True, "parent": dict(parent), "children": serialize_rows(children)})
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/drivers/")
@role_required("ADMIN")
def get_drivers():
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT d.*, u.username, u.is_active AS user_active, b.id AS bus_id, b.bus_number,
                   r.id AS route_id, r.route_name, r.route_code
            FROM drivers d JOIN users u ON u.id = d.user_id
            LEFT JOIN driver_bus_assignments dba ON dba.driver_id = d.id AND dba.is_active = 1
            LEFT JOIN buses b ON b.id = dba.bus_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = b.id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
            ORDER BY d.name
            """
        ).fetchall()
        return rows_response(rows, "drivers")
    finally:
        connection.close()


@core_bp.get("/drivers")
@role_required("ADMIN")
def get_drivers_without_slash():
    return get_drivers()


@core_bp.get("/drivers/me")
@role_required("DRIVER")
def driver_profile():
    connection = get_connection()
    try:
        driver_id = driver_id_for_user(connection, g.user["user_id"])
        row = connection.execute(
            """
            SELECT d.*, u.username, b.id AS bus_id, b.bus_number, r.id AS route_id,
                   r.route_name, r.route_code
            FROM drivers d JOIN users u ON u.id = d.user_id
            LEFT JOIN driver_bus_assignments dba ON dba.driver_id = d.id AND dba.is_active = 1
            LEFT JOIN buses b ON b.id = dba.bus_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = b.id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
            WHERE d.id = ?
            """,
            (driver_id,),
        ).fetchone()
        students = connection.execute(
            """
            SELECT s.*, b.bus_number, ps.stop_name AS pickup_stop_name, ds.stop_name AS drop_stop_name
            FROM students s
            JOIN driver_bus_assignments dba ON dba.bus_id = s.bus_id AND dba.driver_id = ? AND dba.is_active = 1
            LEFT JOIN buses b ON b.id = s.bus_id
            LEFT JOIN stops ps ON ps.id = s.pickup_stop_id
            LEFT JOIN stops ds ON ds.id = s.drop_stop_id
            ORDER BY s.name
            """,
            (driver_id,),
        ).fetchall()
        return jsonify({"success": True, "driver": dict(row), "students": serialize_rows(students)})
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/buses/")
@token_required
def get_buses():
    connection = get_connection()
    try:
        query = """
            SELECT b.*, d.id AS driver_id, d.name AS driver_name,
                   r.id AS route_id, r.route_name, r.route_code
            FROM buses b
            LEFT JOIN driver_bus_assignments dba ON dba.bus_id = b.id AND dba.is_active = 1
            LEFT JOIN drivers d ON d.id = dba.driver_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = b.id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
        """
        params = []
        if g.user["role"] == "DRIVER":
            query += " JOIN driver_bus_assignments scoped_dba ON scoped_dba.bus_id = b.id AND scoped_dba.driver_id = ? AND scoped_dba.is_active = 1"
            params.append(driver_id_for_user(connection, g.user["user_id"]))
        elif g.user["role"] == "PARENT":
            query += " JOIN students scoped_s ON scoped_s.bus_id = b.id JOIN student_parents scoped_sp ON scoped_sp.student_id = scoped_s.id AND scoped_sp.parent_id = ?"
            params.append(parent_id_for_user(connection, g.user["user_id"]))
        query += " ORDER BY b.bus_number"
        rows = connection.execute(query, params).fetchall()
        return rows_response(rows, "buses")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/buses")
@token_required
def get_buses_without_slash():
    return get_buses()


def _bus_access_allowed(connection, bus_id):
    if g.user["role"] == "ADMIN":
        return True
    if g.user["role"] == "DRIVER":
        driver_id = driver_id_for_user(connection, g.user["user_id"])
        return bool(connection.execute(
            "SELECT 1 FROM driver_bus_assignments WHERE bus_id = ? AND driver_id = ? AND is_active = 1",
            (bus_id, driver_id),
        ).fetchone())
    if g.user["role"] == "PARENT":
        parent_id = parent_id_for_user(connection, g.user["user_id"])
        return bool(connection.execute(
            "SELECT 1 FROM student_parents sp JOIN students s ON s.id = sp.student_id WHERE sp.parent_id = ? AND s.bus_id = ?",
            (parent_id, bus_id),
        ).fetchone())
    return False


@core_bp.get("/buses/<int:bus_id>")
@token_required
def get_bus_detail(bus_id):
    connection = get_connection()
    try:
        if not _bus_access_allowed(connection, bus_id):
            return jsonify({"success": False, "error": "Resource not found", "code": "NOT_FOUND"}), 404
        row = connection.execute(
            """
            SELECT b.*, d.id AS driver_id, d.name AS driver_name,
                   r.id AS route_id, r.route_name, r.route_code
            FROM buses b
            LEFT JOIN driver_bus_assignments dba ON dba.bus_id = b.id AND dba.is_active = 1
            LEFT JOIN drivers d ON d.id = dba.driver_id
            LEFT JOIN bus_route_assignments bra ON bra.bus_id = b.id AND bra.is_active = 1
            LEFT JOIN routes r ON r.id = bra.route_id
            WHERE b.id = ?
            """,
            (bus_id,),
        ).fetchone()
        if not row:
            return jsonify({"success": False, "error": "Resource not found", "code": "NOT_FOUND"}), 404
        return row_response(dict(row))
    finally:
        connection.close()


@core_bp.post("/buses/")
@role_required("ADMIN")
def post_bus():
    data = request.get_json(silent=True) or {}
    try:
        bus_number = require_text(data, "bus_number")
        connection = get_connection()
        try:
            cursor = connection.execute(
                "INSERT INTO buses (bus_number, registration_number, capacity, status) VALUES (?, ?, ?, ?)",
                (bus_number, data.get("registration_number"), data.get("capacity"), data.get("status", "ACTIVE")),
            )
            connection.commit()
            return row_response(dict(connection.execute("SELECT * FROM buses WHERE id = ?", (cursor.lastrowid,)).fetchone())), 201
        finally:
            connection.close()
    except Exception as error:
        return error_response(error)


@core_bp.post("/buses")
@role_required("ADMIN")
def post_bus_without_slash():
    return post_bus()


@core_bp.patch("/buses/<int:bus_id>")
@core_bp.put("/buses/<int:bus_id>")
@role_required("ADMIN")
def patch_bus(bus_id):
    data = request.get_json(silent=True) or {}
    connection = get_connection()
    try:
        get_row(connection, "buses", bus_id, "Bus")
        fields = []
        values = []
        for field in ("bus_number", "registration_number", "capacity", "status", "is_active"):
            if field in data:
                fields.append(f"{field} = ?")
                values.append(data[field])
        if "driver_id" in data:
            driver_id = require_id(data, "driver_id")
            get_row(connection, "drivers", driver_id, "Driver")
            connection.execute("UPDATE driver_bus_assignments SET is_active = 0, assigned_until = CURRENT_TIMESTAMP WHERE (bus_id = ? OR driver_id = ?) AND is_active = 1", (bus_id, driver_id))
            connection.execute("INSERT INTO driver_bus_assignments (driver_id, bus_id, assigned_from, is_active) VALUES (?, ?, CURRENT_TIMESTAMP, 1)", (driver_id, bus_id))
        if "route_id" in data:
            route_id = require_id(data, "route_id")
            get_row(connection, "routes", route_id, "Route")
            connection.execute("UPDATE bus_route_assignments SET is_active = 0, assigned_until = CURRENT_TIMESTAMP WHERE bus_id = ? AND is_active = 1", (bus_id,))
            connection.execute("INSERT INTO bus_route_assignments (bus_id, route_id, assigned_from, is_active) VALUES (?, ?, CURRENT_TIMESTAMP, 1)", (bus_id, route_id))
        if fields:
            values.append(bus_id)
            connection.execute(f"UPDATE buses SET {', '.join(fields)} WHERE id = ?", values)
        connection.commit()
        return row_response(dict(connection.execute("SELECT * FROM buses WHERE id = ?", (bus_id,)).fetchone()))
    except Exception as error:
        connection.rollback()
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/routes/")
@token_required
def get_routes():
    connection = get_connection()
    try:
        query = "SELECT DISTINCT r.* FROM routes r"
        params = []
        if g.user["role"] == "DRIVER":
            query += " JOIN bus_route_assignments scoped_bra ON scoped_bra.route_id = r.id JOIN driver_bus_assignments scoped_dba ON scoped_dba.bus_id = scoped_bra.bus_id AND scoped_dba.driver_id = ? AND scoped_dba.is_active = 1 WHERE scoped_bra.is_active = 1"
            params.append(driver_id_for_user(connection, g.user["user_id"]))
        elif g.user["role"] == "PARENT":
            query += " JOIN bus_route_assignments scoped_bra ON scoped_bra.route_id = r.id JOIN students scoped_s ON scoped_s.bus_id = scoped_bra.bus_id JOIN student_parents scoped_sp ON scoped_sp.student_id = scoped_s.id AND scoped_sp.parent_id = ? WHERE scoped_bra.is_active = 1"
            params.append(parent_id_for_user(connection, g.user["user_id"]))
        query += " ORDER BY r.route_name"
        rows = connection.execute(query, params).fetchall()
        return rows_response(rows, "routes")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/routes")
@token_required
def get_routes_without_slash():
    return get_routes()


@core_bp.post("/routes/")
@role_required("ADMIN")
def post_route():
    data = request.get_json(silent=True) or {}
    try:
        route_name = require_text(data, "route_name")
        route_code = require_text(data, "route_code")
        connection = get_connection()
        try:
            cursor = connection.execute("INSERT INTO routes (route_name, route_code, description, is_active) VALUES (?, ?, ?, ?)", (route_name, route_code, data.get("description"), data.get("is_active", 1)))
            connection.commit()
            return row_response(dict(connection.execute("SELECT * FROM routes WHERE id = ?", (cursor.lastrowid,)).fetchone())), 201
        finally:
            connection.close()
    except Exception as error:
        return error_response(error)


@core_bp.post("/routes")
@role_required("ADMIN")
def post_route_without_slash():
    return post_route()


@core_bp.patch("/routes/<int:route_id>")
@core_bp.put("/routes/<int:route_id>")
@role_required("ADMIN")
def patch_route(route_id):
    data = request.get_json(silent=True) or {}
    connection = get_connection()
    try:
        get_row(connection, "routes", route_id, "Route")
        fields = []
        values = []
        for field in ("route_name", "route_code", "description", "is_active"):
            if field in data:
                fields.append(f"{field} = ?")
                values.append(data[field])
        if not fields:
            raise DomainValidationError("At least one route field is required", "NO_UPDATE_FIELDS")
        values.append(route_id)
        connection.execute(f"UPDATE routes SET {', '.join(fields)} WHERE id = ?", values)
        connection.commit()
        return row_response(dict(connection.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()))
    except Exception as error:
        connection.rollback()
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/routes/<int:route_id>/stops")
@token_required
def get_stops(route_id):
    connection = get_connection()
    try:
        get_row(connection, "routes", route_id, "Route")
        rows = connection.execute("SELECT * FROM stops WHERE route_id = ? ORDER BY stop_order", (route_id,)).fetchall()
        return rows_response(rows, "stops")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.post("/routes/<int:route_id>/stops")
@role_required("ADMIN")
def post_stop(route_id):
    data = request.get_json(silent=True) or {}
    connection = get_connection()
    try:
        get_row(connection, "routes", route_id, "Route")
        stop_name = require_text(data, "stop_name")
        latitude, longitude = validate_coordinates(data.get("latitude"), data.get("longitude"))
        stop_order = require_id(data, "stop_order")
        cursor = connection.execute(
            "INSERT INTO stops (route_id, stop_name, latitude, longitude, stop_order, scheduled_pickup_time, scheduled_drop_time, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (route_id, stop_name, latitude, longitude, stop_order, data.get("scheduled_pickup_time"), data.get("scheduled_drop_time"), data.get("is_active", 1)),
        )
        connection.commit()
        return row_response(dict(connection.execute("SELECT * FROM stops WHERE id = ?", (cursor.lastrowid,)).fetchone())), 201
    except Exception as error:
        connection.rollback()
        return error_response(error)
    finally:
        connection.close()


@core_bp.patch("/stops/<int:stop_id>")
@core_bp.put("/stops/<int:stop_id>")
@role_required("ADMIN")
def patch_stop(stop_id):
    data = request.get_json(silent=True) or {}
    connection = get_connection()
    try:
        stop = get_row(connection, "stops", stop_id, "Stop")
        fields = []
        values = []
        if "stop_name" in data:
            fields.append("stop_name = ?")
            values.append(require_text(data, "stop_name"))
        if "latitude" in data or "longitude" in data:
            latitude, longitude = validate_coordinates(data.get("latitude", stop["latitude"]), data.get("longitude", stop["longitude"]))
            fields.extend(["latitude = ?", "longitude = ?"])
            values.extend([latitude, longitude])
        for field in ("stop_order", "scheduled_pickup_time", "scheduled_drop_time", "is_active"):
            if field in data:
                fields.append(f"{field} = ?")
                values.append(data[field])
        if not fields:
            raise DomainValidationError("At least one stop field is required", "NO_UPDATE_FIELDS")
        values.append(stop_id)
        connection.execute(f"UPDATE stops SET {', '.join(fields)} WHERE id = ?", values)
        connection.commit()
        return row_response(dict(connection.execute("SELECT * FROM stops WHERE id = ?", (stop_id,)).fetchone()))
    except Exception as error:
        connection.rollback()
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/trips/")
@token_required
def get_trips():
    connection = get_connection()
    try:
        query = "SELECT t.*, b.bus_number, r.route_name, r.route_code, d.name AS driver_name FROM trips t JOIN buses b ON b.id = t.bus_id JOIN routes r ON r.id = t.route_id JOIN drivers d ON d.id = t.driver_id"
        params = []
        if g.user["role"] == "DRIVER":
            query += " WHERE t.driver_id = ?"
            params.append(driver_id_for_user(connection, g.user["user_id"]))
        elif g.user["role"] == "PARENT":
            query += " JOIN student_parents sp ON sp.parent_id = ? JOIN students s ON s.id = sp.student_id AND s.bus_id = t.bus_id"
            params.append(parent_id_for_user(connection, g.user["user_id"]))
        query += " ORDER BY t.trip_date DESC, t.id DESC"
        return rows_response(connection.execute(query, params).fetchall(), "trips")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/trips")
@token_required
def get_trips_without_slash():
    return get_trips()


@core_bp.post("/trips/")
@role_required("ADMIN", "DRIVER")
def post_trip():
    try:
        return row_response(create_trip(request.get_json(silent=True) or {}, g.user)), 201
    except Exception as error:
        return error_response(error)


@core_bp.post("/trips")
@role_required("ADMIN", "DRIVER")
def post_trip_without_slash():
    return post_trip()


@core_bp.get("/attendance/")
@token_required
def get_attendance():
    connection = get_connection()
    try:
        query = "SELECT a.*, s.name AS student_name, s.student_code, t.trip_type, t.trip_date, t.bus_id, t.route_id FROM attendance a JOIN students s ON s.id = a.student_id JOIN trips t ON t.id = a.trip_id"
        params = []
        if g.user["role"] == "PARENT":
            query += " JOIN student_parents sp ON sp.student_id = a.student_id WHERE sp.parent_id = ?"
            params.append(parent_id_for_user(connection, g.user["user_id"]))
        elif g.user["role"] == "DRIVER":
            query += " WHERE t.driver_id = ?"
            params.append(driver_id_for_user(connection, g.user["user_id"]))
        query += " ORDER BY a.recorded_at DESC"
        return rows_response(connection.execute(query, params).fetchall(), "attendance")
    except DomainValidationError as error:
        return error_response(error)
    finally:
        connection.close()


@core_bp.get("/attendance")
@token_required
def get_attendance_without_slash():
    return get_attendance()


@core_bp.post("/attendance/")
@role_required("ADMIN", "DRIVER")
def post_attendance():
    try:
        return row_response(create_attendance(request.get_json(silent=True) or {}, g.user)), 201
    except Exception as error:
        return error_response(error)


@core_bp.post("/attendance")
@role_required("ADMIN", "DRIVER")
def post_attendance_without_slash():
    return post_attendance()
