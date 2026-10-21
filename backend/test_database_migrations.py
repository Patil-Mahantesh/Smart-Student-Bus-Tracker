
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from config import Config
from database import (
    get_connection,
    initialize_database,
    migrate_core_schema,
)


class DatabaseMigrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "migration_test.db",
        )

        self.config_patch = patch.object(
            Config,
            "DATABASE_PATH",
            self.db_path,
        )
        self.config_patch.start()

        self.addCleanup(self.config_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def test_initialization_can_run_twice(self):
        initialize_database()
        initialize_database()

        connection = get_connection()
        try:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            for table in (
                "users",
                "students",
                "trips",
                "attendance",
                "driver_bus_assignments",
            ):
                self.assertIn(table, tables)

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )
        finally:
            connection.close()

    def test_attendance_indexes_exist_after_initialization(self):
        initialize_database()

        connection = get_connection()
        try:
            indexes = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'index'
                    AND tbl_name = 'attendance'
                    """
                )
            }

            expected = {
                "idx_attendance_trip",
                "idx_attendance_student",
                "idx_attendance_date",
                "idx_attendance_recorded_by",
            }

            self.assertTrue(expected.issubset(indexes))
        finally:
            connection.close()

    def test_duplicate_employee_ids_fail_without_losing_records(self):
        initialize_database()

        connection = get_connection()
        try:
            connection.execute(
                "DROP INDEX IF EXISTS idx_drivers_employee_id"
            )

            user_ids = []

            for username in (
                "migration_driver_a",
                "migration_driver_b",
            ):
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, role
                    )
                    VALUES (?, ?, 'DRIVER')
                    """,
                    (username, "test-only-hash"),
                )
                user_ids.append(cursor.lastrowid)

            for user_id, name in zip(
                user_ids,
                ("Driver A", "Driver B"),
            ):
                connection.execute(
                    """
                    INSERT INTO drivers (
                        user_id, name, employee_id
                    )
                    VALUES (?, ?, ?)
                    """,
                    (user_id, name, "DUPLICATE-ID"),
                )

            connection.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                migrate_core_schema(connection)

            count = connection.execute(
                """
                SELECT COUNT(*)
                FROM drivers
                WHERE employee_id = 'DUPLICATE-ID'
                """
            ).fetchone()[0]

            self.assertEqual(count, 2)
        finally:
            connection.close()

    def test_failed_initialization_does_not_corrupt_database(self):
        initialize_database()

        connection = get_connection()
        try:
            connection.execute(
                "DROP INDEX IF EXISTS idx_drivers_employee_id"
            )

            user_ids = []

            for username in (
                "rollback_driver_a",
                "rollback_driver_b",
            ):
                cursor = connection.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, role
                    )
                    VALUES (?, ?, 'DRIVER')
                    """,
                    (username, "test-only-hash"),
                )
                user_ids.append(cursor.lastrowid)

            for user_id, name in zip(
                user_ids,
                ("Rollback Driver A", "Rollback Driver B"),
            ):
                connection.execute(
                    """
                    INSERT INTO drivers (
                        user_id, name, employee_id
                    )
                    VALUES (?, ?, ?)
                    """,
                    (user_id, name, "ROLLBACK-DUPLICATE"),
                )

            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            initialize_database()

        connection = get_connection()
        try:
            count = connection.execute(
                """
                SELECT COUNT(*)
                FROM drivers
                WHERE employee_id = 'ROLLBACK-DUPLICATE'
                """
            ).fetchone()[0]

            self.assertEqual(count, 2)

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )
        finally:
            connection.close()

    def test_legacy_attendance_migration_preserves_records(self):
        initialize_database()

        connection = get_connection()
        try:
            user_id = connection.execute(
                """
                INSERT INTO users (
                    username, password_hash, role
                )
                VALUES ('legacy_test_driver', 'test-hash', 'DRIVER')
                """
            ).lastrowid

            driver_id = connection.execute(
                """
                INSERT INTO drivers (user_id, name)
                VALUES (?, ?)
                """,
                (user_id, "Legacy Test Driver"),
            ).lastrowid

            bus_id = connection.execute(
                """
                INSERT INTO buses (bus_number)
                VALUES (?)
                """,
                ("LEGACY-TEST-BUS",),
            ).lastrowid

            route_id = connection.execute(
                """
                INSERT INTO routes (route_name)
                VALUES (?)
                """,
                ("Legacy Test Route",),
            ).lastrowid

            student_id = connection.execute(
                """
                INSERT INTO students (student_code, name)
                VALUES (?, ?)
                """,
                ("LEGACY-TEST-STUDENT", "Legacy Test Student"),
            ).lastrowid

            trip_id = connection.execute(
                """
                INSERT INTO trips (
                    bus_id, route_id, driver_id,
                    trip_type, status
                )
                VALUES (?, ?, ?, 'PICKUP', 'COMPLETED')
                """,
                (bus_id, route_id, driver_id),
            ).lastrowid

            # Replace attendance with a legacy table that has no
            # attendance_date column.
            connection.execute(
                "ALTER TABLE attendance RENAME TO attendance_old"
            )

            connection.execute(
                """
                CREATE TABLE attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    attendance_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    recorded_by INTEGER,
                    method TEXT DEFAULT 'MANUAL',
                    recognized_at DATETIME,
                    latitude REAL,
                    longitude REAL,
                    confidence REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            connection.execute(
                """
                INSERT INTO attendance (
                    id, trip_id, student_id,
                    attendance_type, status, created_at
                )
                VALUES (?, ?, ?, 'PICKUP', 'PRESENT', ?)
                """,
                (
                    501,
                    trip_id,
                    student_id,
                    "2026-10-20 08:30:00",
                ),
            )

            connection.execute("DROP TABLE attendance_old")
            connection.commit()

            # Run the schema migration.
            migrate_core_schema(connection)
            connection.commit()

            migrated = connection.execute(
                """
                SELECT
                    id,
                    trip_id,
                    student_id,
                    attendance_type,
                    status,
                    attendance_date
                FROM attendance
                WHERE id = 501
                """
            ).fetchone()

            self.assertIsNotNone(migrated)
            self.assertEqual(migrated["trip_id"], trip_id)
            self.assertEqual(migrated["student_id"], student_id)
            self.assertEqual(migrated["attendance_type"], "PICKUP")
            self.assertEqual(migrated["status"], "PRESENT")
            self.assertEqual(
                migrated["attendance_date"],
                "2026-10-20",
            )

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
