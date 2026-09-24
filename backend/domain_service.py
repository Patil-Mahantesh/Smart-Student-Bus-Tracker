from datetime import date

from database import get_connection


class DomainValidationError(ValueError):
    def __init__(self, message, code="VALIDATION_ERROR", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def require_text(data, field):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field} is required", f"MISSING_{field.upper()}")
    return value.strip()


def require_id(data, field):
    value = data.get(field)
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise DomainValidationError(f"{field} must be a valid integer", f"INVALID_{field.upper()}")
    if value <= 0:
        raise DomainValidationError(f"{field} must be positive", f"INVALID_{field.upper()}")
    return value


def optional_id(data, field):
    value = data.get(field)
    if value in (None, ""):
        return None
    return require_id(data, field)


def get_row(connection, table, row_id, label):
    row = connection.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (row_id,),
    ).fetchone()
    if not row:
        raise DomainValidationError(f"{label} not found", f"{label.upper()}_NOT_FOUND", 404)
    return row


def validate_coordinates(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise DomainValidationError("latitude and longitude must be numbers", "INVALID_COORDINATES")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise DomainValidationError("latitude or longitude is out of range", "INVALID_COORDINATES")
    return latitude, longitude


def ensure_student_relationships(connection, data):
    bus_id = optional_id(data, "bus_id")
    pickup_stop_id = optional_id(data, "pickup_stop_id")
    drop_stop_id = optional_id(data, "drop_stop_id")

    if bus_id:
        get_row(connection, "buses", bus_id, "Bus")
    for stop_id in (pickup_stop_id, drop_stop_id):
        if stop_id:
            get_row(connection, "stops", stop_id, "Stop")

    if pickup_stop_id or drop_stop_id:
        stop_ids = [stop_id for stop_id in (pickup_stop_id, drop_stop_id) if stop_id]
        placeholders = ",".join("?" for _ in stop_ids)
        rows = connection.execute(
            f"SELECT id FROM stops WHERE id IN ({placeholders})",
            stop_ids,
        ).fetchall()
        if len(rows) != len(stop_ids):
            raise DomainValidationError("Student stop assignment is invalid", "INVALID_STOP_ASSIGNMENT")

    return bus_id, pickup_stop_id, drop_stop_id


def create_student(data):
    name = require_text(data, "name")
    student_code = require_text(data, "student_code")
    bus_id, pickup_stop_id, drop_stop_id = (None, None, None)
    connection = get_connection()
    try:
        bus_id, pickup_stop_id, drop_stop_id = ensure_student_relationships(connection, data)
        cursor = connection.execute(
            """
            INSERT INTO students
                (name, student_code, bus_id, pickup_stop_id, drop_stop_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, student_code, bus_id, pickup_stop_id, drop_stop_id, data.get("status", "ACTIVE")),
        )
        connection.commit()
        return get_student(connection, cursor.lastrowid)
    except DomainValidationError:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        if "UNIQUE constraint failed: students.student_code" in str(error):
            raise DomainValidationError("student_code already exists", "DUPLICATE_STUDENT_CODE", 409)
        raise
    finally:
        connection.close()


def get_student(connection, student_id):
    row = connection.execute(
        """
        SELECT s.*, b.bus_number,
               ps.stop_name AS pickup_stop_name,
               ds.stop_name AS drop_stop_name
        FROM students s
        LEFT JOIN buses b ON b.id = s.bus_id
        LEFT JOIN stops ps ON ps.id = s.pickup_stop_id
        LEFT JOIN stops ds ON ds.id = s.drop_stop_id
        WHERE s.id = ?
        """,
        (student_id,),
    ).fetchone()
    if not row:
        raise DomainValidationError("Student not found", "STUDENT_NOT_FOUND", 404)
    return dict(row)


def update_student(student_id, data):
    connection = get_connection()
    try:
        get_row(connection, "students", student_id, "Student")
        bus_id, pickup_stop_id, drop_stop_id = ensure_student_relationships(connection, data)
        fields = []
        values = []
        for field in ("name", "student_code", "status"):
            if field in data:
                fields.append(f"{field} = ?")
                values.append(require_text(data, field))
        for field, value in (("bus_id", bus_id), ("pickup_stop_id", pickup_stop_id), ("drop_stop_id", drop_stop_id)):
            if field in data:
                fields.append(f"{field} = ?")
                values.append(value)
        if not fields:
            raise DomainValidationError("At least one student field is required", "NO_UPDATE_FIELDS")
        values.append(student_id)
        connection.execute(f"UPDATE students SET {', '.join(fields)} WHERE id = ?", values)
        connection.commit()
        return get_student(connection, student_id)
    except DomainValidationError:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        if "UNIQUE constraint failed: students.student_code" in str(error):
            raise DomainValidationError("student_code already exists", "DUPLICATE_STUDENT_CODE", 409)
        raise
    finally:
        connection.close()


def serialize_rows(rows):
    return [dict(row) for row in rows]


def parent_id_for_user(connection, user_id):
    row = connection.execute("SELECT id FROM parents WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise DomainValidationError("Parent profile not found", "PARENT_NOT_FOUND", 404)
    return row["id"]


def driver_id_for_user(connection, user_id):
    row = connection.execute("SELECT id FROM drivers WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        raise DomainValidationError("Driver profile not found", "DRIVER_NOT_FOUND", 404)
    return row["id"]


def validate_trip_graph(connection, bus_id, route_id, driver_id):
    get_row(connection, "buses", bus_id, "Bus")
    get_row(connection, "routes", route_id, "Route")
    get_row(connection, "drivers", driver_id, "Driver")
    assignment = connection.execute(
        """
        SELECT 1 FROM driver_bus_assignments
        WHERE driver_id = ? AND bus_id = ? AND is_active = 1
        """,
        (driver_id, bus_id),
    ).fetchone()
    if not assignment:
        raise DomainValidationError("Driver is not assigned to this bus", "DRIVER_BUS_MISMATCH", 409)


def create_trip(data, acting_user):
    bus_id = require_id(data, "bus_id")
    route_id = require_id(data, "route_id")
    trip_type = require_text(data, "trip_type").upper()
    if trip_type not in ("PICKUP", "DROP"):
        raise DomainValidationError("trip_type must be PICKUP or DROP", "INVALID_TRIP_TYPE")
    connection = get_connection()
    try:
        driver_id = optional_id(data, "driver_id")
        if acting_user["role"] == "DRIVER":
            driver_id = driver_id_for_user(connection, acting_user["user_id"])
        if not driver_id:
            raise DomainValidationError("driver_id is required", "MISSING_DRIVER_ID")
        validate_trip_graph(connection, bus_id, route_id, driver_id)
        trip_date = data.get("trip_date") or date.today().isoformat()
        status = data.get("status", "SCHEDULED").upper()
        if status not in ("SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"):
            raise DomainValidationError("Invalid trip status", "INVALID_TRIP_STATUS")
        cursor = connection.execute(
            """
            INSERT INTO trips (bus_id, route_id, driver_id, trip_type, status, trip_date, started_at)
            VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? = 'IN_PROGRESS' THEN CURRENT_TIMESTAMP ELSE NULL END)
            """,
            (bus_id, route_id, driver_id, trip_type, status, trip_date, status),
        )
        connection.commit()
        return dict(connection.execute("SELECT * FROM trips WHERE id = ?", (cursor.lastrowid,)).fetchone())
    except DomainValidationError:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_attendance(data, acting_user):
    trip_id = require_id(data, "trip_id")
    student_id = require_id(data, "student_id")
    attendance_type = require_text(data, "attendance_type").upper()
    status = require_text(data, "status").upper()
    method = data.get("method", "MANUAL").upper()
    if attendance_type not in ("PICKUP", "DROP"):
        raise DomainValidationError("attendance_type must be PICKUP or DROP", "INVALID_ATTENDANCE_TYPE")
    if status not in ("PRESENT", "ABSENT", "PENDING"):
        raise DomainValidationError("status must be PRESENT, ABSENT, or PENDING", "INVALID_ATTENDANCE_STATUS")
    if method not in ("MANUAL", "FACE_RECOGNITION"):
        raise DomainValidationError("Invalid attendance method", "INVALID_ATTENDANCE_METHOD")
    connection = get_connection()
    try:
        trip = get_row(connection, "trips", trip_id, "Trip")
        get_row(connection, "students", student_id, "Student")
        if acting_user["role"] == "DRIVER":
            driver_id = driver_id_for_user(connection, acting_user["user_id"])
            if trip["driver_id"] != driver_id:
                raise DomainValidationError("Driver is not assigned to this trip", "TRIP_ACCESS_DENIED", 403)
        connection.execute(
            """
            INSERT INTO attendance
                (trip_id, student_id, attendance_type, attendance_date, status, recorded_by, method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trip_id, student_id, attendance_type) DO UPDATE SET
                attendance_date = excluded.attendance_date,
                status = excluded.status,
                recorded_by = excluded.recorded_by,
                method = excluded.method,
                recorded_at = CURRENT_TIMESTAMP
            """,
            (trip_id, student_id, attendance_type, data.get("attendance_date", date.today().isoformat()),
             status, acting_user["user_id"], method),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM attendance WHERE trip_id = ? AND student_id = ? AND attendance_type = ?", (trip_id, student_id, attendance_type)).fetchone()
        return dict(row)
    except DomainValidationError:
        connection.rollback()
        raise
    finally:
        connection.close()
