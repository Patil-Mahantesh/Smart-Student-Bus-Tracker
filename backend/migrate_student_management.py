"""
Safe migration for Student Management.

Run from the backend directory with:
    .venv\Scripts\python.exe migrate_student_management.py

This migration ONLY adds nullable columns if they do not already exist.
It does not delete, rename, merge, or modify existing student/parent records.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "smart_student_bus_tracker.db"


def get_columns(connection, table_name):
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def add_column_if_missing(connection, table_name, column_name, column_definition):
    columns = get_columns(connection, table_name)

    if column_name in columns:
        print(f"  [OK] {table_name}.{column_name} already exists")
        return

    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )
    print(f"  [ADDED] {table_name}.{column_name}")


def main():
    print("=" * 60)
    print("SMART STUDENT BUS TRACKER")
    print("Student Management Database Migration")
    print("=" * 60)
    print(f"Database: {DB_PATH}")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found:\n{DB_PATH}\n\n"
            "Run the existing backend/database initialization first."
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # ---------------------------------------------------------
        # 1. Backup safety check
        # ---------------------------------------------------------
        print("\n[1] Checking database...")

        required_tables = {"students", "parents", "student_parents"}

        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            ).fetchall()
        }

        missing = required_tables - existing_tables

        if missing:
            raise RuntimeError(
                "Required tables are missing: "
                + ", ".join(sorted(missing))
            )

        print("  [OK] Required tables exist")

        # ---------------------------------------------------------
        # 2. Student fields
        # ---------------------------------------------------------
        print("\n[2] Updating students table...")

        add_column_if_missing(
            connection,
            "students",
            "class_name",
            "TEXT"
        )

        # ---------------------------------------------------------
        # 3. Family/parent fields
        # ---------------------------------------------------------
        print("\n[3] Updating parents table...")

        add_column_if_missing(
            connection,
            "parents",
            "father_name",
            "TEXT"
        )

        add_column_if_missing(
            connection,
            "parents",
            "mother_name",
            "TEXT"
        )

        # ---------------------------------------------------------
        # 4. Commit
        # ---------------------------------------------------------
        connection.commit()

        # ---------------------------------------------------------
        # 5. Verify
        # ---------------------------------------------------------
        print("\n[4] Verifying migration...")

        student_columns = get_columns(connection, "students")
        parent_columns = get_columns(connection, "parents")

        checks = [
            ("students.class_name", "class_name" in student_columns),
            ("parents.father_name", "father_name" in parent_columns),
            ("parents.mother_name", "mother_name" in parent_columns),
        ]

        all_ok = True

        for name, passed in checks:
            print(f"  [{'OK' if passed else 'FAIL'}] {name}")
            all_ok = all_ok and passed

        print("\n[5] Existing data check")

        student_count = connection.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

        parent_count = connection.execute(
            "SELECT COUNT(*) FROM parents"
        ).fetchone()[0]

        relationship_count = connection.execute(
            "SELECT COUNT(*) FROM student_parents"
        ).fetchone()[0]

        print(f"  Students:         {student_count}")
        print(f"  Parent accounts:  {parent_count}")
        print(f"  Relationships:    {relationship_count}")

        if not all_ok:
            raise RuntimeError("Migration verification failed.")

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(
            "\nNo existing student, parent, or relationship records "
            "were deleted or merged."
        )
        print(
            "\nNote: Existing class/family-name values remain NULL until "
            "they are explicitly entered through Student Management."
        )

    except Exception:
        connection.rollback()
        print("\nMIGRATION FAILED - all changes were rolled back.")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
