
from werkzeug.security import generate_password_hash
import sqlite3
from config import Config


def get_connection():
    connection = sqlite3.connect(Config.DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('PARENT', 'DRIVER', 'ADMIN')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            revoked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            father_name TEXT,
            mother_name TEXT,
            phone TEXT,
            email TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            license_number TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            stop_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            stop_order INTEGER NOT NULL,
            FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE,
            UNIQUE (route_id, stop_order)
        );

        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL UNIQUE,
            registration_number TEXT UNIQUE,
            capacity INTEGER,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bus_route_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            assigned_from DATETIME,
            assigned_until DATETIME,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
            FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            class_name TEXT,
            pickup_stop_id INTEGER,
            drop_stop_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pickup_stop_id) REFERENCES stops(id) ON DELETE SET NULL,
            FOREIGN KEY (drop_stop_id) REFERENCES stops(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS student_parents (
            student_id INTEGER NOT NULL,
            parent_id INTEGER NOT NULL,
            relationship TEXT,
            is_primary INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (student_id, parent_id),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            model_name TEXT NOT NULL,
            model_version TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            trip_type TEXT NOT NULL CHECK (trip_type IN ('PICKUP', 'DROP')),
            status TEXT NOT NULL CHECK (
                status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')
            ),
            started_at DATETIME,
            ended_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_id) REFERENCES buses(id),
            FOREIGN KEY (route_id) REFERENCES routes(id),
            FOREIGN KEY (driver_id) REFERENCES drivers(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            attendance_type TEXT NOT NULL CHECK (
                attendance_type IN ('PICKUP', 'DROP')
            ),
            status TEXT NOT NULL CHECK (
                status IN ('PRESENT', 'ABSENT', 'PENDING')
            ),
            attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
            recognized_at DATETIME,
            recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            recorded_by INTEGER,
            method TEXT NOT NULL DEFAULT 'MANUAL' CHECK (
                method IN ('FACE_RECOGNITION', 'MANUAL')
            ),
            latitude REAL,
            longitude REAL,
            confidence REAL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (trip_id, student_id, attendance_type),
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS travel_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('COMING', 'NOT_COMING')
            ),
            travel_date DATE NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (student_id, travel_date),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS bus_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed REAL,
            recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            trip_id INTEGER,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date DATETIME NOT NULL,
            created_by INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NEW',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_stops_route
            ON stops(route_id);

        CREATE INDEX IF NOT EXISTS idx_students_active
            ON students(is_active);

        CREATE INDEX IF NOT EXISTS idx_trips_bus
            ON trips(bus_id);

        CREATE INDEX IF NOT EXISTS idx_trips_driver
            ON trips(driver_id);

        CREATE INDEX IF NOT EXISTS idx_attendance_trip
            ON attendance(trip_id);

        CREATE INDEX IF NOT EXISTS idx_attendance_student
            ON attendance(student_id);

        CREATE INDEX IF NOT EXISTS idx_travel_status_date
            ON travel_status(travel_date);

        CREATE INDEX IF NOT EXISTS idx_bus_locations_trip_time
            ON bus_locations(trip_id, recorded_at);

        CREATE INDEX IF NOT EXISTS idx_notifications_parent
            ON notifications(parent_id, is_read);

        CREATE TABLE IF NOT EXISTS driver_bus_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            assigned_from TEXT NOT NULL,
            assigned_until TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (driver_id) REFERENCES drivers(id),
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        );

        CREATE INDEX IF NOT EXISTS idx_driver_bus_active
            ON driver_bus_assignments(driver_id, is_active);  

            
        """
    )
    migrate_core_schema(connection)
    connection.commit()
    connection.close()


def _table_columns(connection, table_name):
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _add_column_if_missing(connection, table_name, column_name, definition):
    if column_name not in _table_columns(connection, table_name):
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def migrate_core_schema(connection):
    """Apply additive upgrades while retaining the existing SQLite records."""
    _add_column_if_missing(connection, "drivers", "employee_id", "TEXT")
    _add_column_if_missing(connection, "drivers", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(connection, "buses", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(connection, "routes", "route_code", "TEXT")
    _add_column_if_missing(connection, "stops", "scheduled_pickup_time", "TEXT")
    _add_column_if_missing(connection, "stops", "scheduled_drop_time", "TEXT")
    _add_column_if_missing(connection, "stops", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(connection, "students", "bus_id", "INTEGER REFERENCES buses(id) ON DELETE SET NULL")
    _add_column_if_missing(connection, "students", "status", "TEXT NOT NULL DEFAULT 'ACTIVE'")
    _add_column_if_missing(connection, "students", "class_name", "TEXT")
    _add_column_if_missing(connection, "parents", "father_name", "TEXT")
    _add_column_if_missing(connection, "parents", "mother_name", "TEXT")
    _add_column_if_missing(connection, "trips", "trip_date", "DATE")

    connection.execute(
        "UPDATE routes SET route_code = 'ROUTE-' || id WHERE route_code IS NULL"
    )
    connection.execute(
        "UPDATE trips SET trip_date = DATE(COALESCE(started_at, created_at, CURRENT_TIMESTAMP)) "
        "WHERE trip_date IS NULL"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_routes_code ON routes(route_code)"
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_drivers_employee_id "
        "ON drivers(employee_id) WHERE employee_id IS NOT NULL"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_students_bus ON students(bus_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_trips_date ON trips(trip_date)"
    )

    attendance_columns = _table_columns(connection, "attendance")
    if "attendance_date" not in attendance_columns:
        connection.execute("ALTER TABLE attendance RENAME TO attendance_legacy")
        connection.execute(
            """
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                attendance_type TEXT NOT NULL CHECK (attendance_type IN ('PICKUP', 'DROP')),
                attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
                status TEXT NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'PENDING')),
                recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                recorded_by INTEGER,
                method TEXT NOT NULL DEFAULT 'MANUAL' CHECK (method IN ('FACE_RECOGNITION', 'MANUAL')),
                recognized_at DATETIME,
                latitude REAL,
                longitude REAL,
                confidence REAL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (trip_id, student_id, attendance_type),
                FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO attendance (
                id, trip_id, student_id, attendance_type, attendance_date,
                status, recognized_at, latitude, longitude, confidence, created_at
            )
            SELECT id, trip_id, student_id, attendance_type,
                   DATE(COALESCE(created_at, CURRENT_TIMESTAMP)),
                   CASE WHEN status = 'NOT_EXPECTED' THEN 'PENDING' ELSE status END,
                   recognized_at, latitude, longitude, confidence, created_at
            FROM attendance_legacy
            """
        )
        connection.execute("DROP TABLE attendance_legacy")

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_attendance_recorded_by ON attendance(recorded_by)"
    )
    connection.execute(
        """
        UPDATE driver_bus_assignments
        SET is_active = 0, assigned_until = COALESCE(assigned_until, CURRENT_TIMESTAMP)
        WHERE is_active = 1
          AND id NOT IN (
              SELECT MAX(id) FROM driver_bus_assignments
              WHERE is_active = 1 GROUP BY driver_id
          )
        """
    )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_driver_bus "
        "ON driver_bus_assignments(driver_id) WHERE is_active = 1"
    )


def create_admin():
    connection = get_connection()

    username = "admin"
    password = "Admin@123"
    name = "System Administrator"

    existing_user = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing_user:
        print("Admin account already exists.")
        connection.close()
        return

    password_hash = generate_password_hash(password)

    cursor = connection.execute(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
        """,
        (username, password_hash, "ADMIN")
    )

    user_id = cursor.lastrowid

    connection.execute(
        """
        INSERT INTO admins (user_id, name)
        VALUES (?, ?)
        """,
        (user_id, name)
    )

    connection.commit()
    connection.close()

    print("Admin account created successfully.")
    print("Username: admin")
    print("Password: Admin@123")


if __name__ == "__main__":
    initialize_database()
    create_admin()