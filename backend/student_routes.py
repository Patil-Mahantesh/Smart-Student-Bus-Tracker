from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from secrets import token_urlsafe
from pathlib import Path

from auth import role_required
from database import get_connection


student_bp = Blueprint(
    "students",
    __name__,
    url_prefix="/api/students",
)


# ============================================================
# HELPERS
# ============================================================

def generate_student_code(connection):
    """
    Generate the next student code.

    Example:
        STU001
        STU002
        STU003
    """

    rows = connection.execute(
        """
        SELECT student_code
        FROM students
        WHERE student_code LIKE 'STU%'
        """
    ).fetchall()

    highest = 0

    for row in rows:
        code = row["student_code"] or ""

        if not code.startswith("STU"):
            continue

        suffix = code[3:]

        if suffix.isdigit():
            highest = max(
                highest,
                int(suffix)
            )

    return f"STU{highest + 1:03d}"


def generate_parent_username(connection):
    """
    Generate the next family login ID.

    Example:
        parent00001
        parent00002
        parent00003
    """

    rows = connection.execute(
        """
        SELECT username
        FROM users
        WHERE role = 'PARENT'
          AND username LIKE 'parent%'
        """
    ).fetchall()

    highest = 0

    for row in rows:
        username = row["username"] or ""

        suffix = username[len("parent"):]

        if suffix.isdigit():
            highest = max(
                highest,
                int(suffix)
            )

    return f"parent{highest + 1:05d}"


def generate_temporary_password():
    """
    Generate a temporary family password.

    The password is returned only in the create-student
    response so the Admin can provide it to the family.
    """

    return (
        "Parent@"
        + token_urlsafe(6)
        .replace("-", "")
        .replace("_", "")[:8]
    )


def get_student_parent(connection, student_id):
    """
    Return the primary/first family account associated
    with the student.
    """

    row = connection.execute(
        """
        SELECT
            p.id,
            p.user_id,
            p.name,
            p.father_name,
            p.mother_name,
            p.phone,
            p.email,
            u.username
        FROM student_parents sp
        JOIN parents p
          ON p.id = sp.parent_id
        JOIN users u
          ON u.id = p.user_id
        WHERE sp.student_id = ?
        ORDER BY
            sp.is_primary DESC,
            p.id ASC
        LIMIT 1
        """,
        (student_id,)
    ).fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "name": row["name"],
        "father_name": row["father_name"],
        "mother_name": row["mother_name"],
        "phone": row["phone"],
        "email": row["email"],
    }


def get_student_dict(connection, student):
    """
    Convert a student DB row into the response structure
    expected by the React Student Management screen.
    """

    face = connection.execute(
        """
        SELECT id
        FROM face_embeddings
        WHERE student_id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (student["id"],)
    ).fetchone()

    parent = get_student_parent(
        connection,
        student["id"]
    )

    return {
        "id": student["id"],
        "student_code": student["student_code"],
        "name": student["name"],
        "class_name": student["class_name"],
        "pickup_stop_id": student["pickup_stop_id"],
        "drop_stop_id": student["drop_stop_id"],
        "bus_id": student["bus_id"],
        "status": student["status"],
        "is_active": student["is_active"],
        "created_at": student["created_at"],
        "has_face": bool(face),
        "parent": parent,
    }


def find_parent_by_username(connection, username):
    """
    Find an existing family account by parent username.
    """

    return connection.execute(
        """
        SELECT
            p.id,
            p.user_id,
            p.name,
            p.father_name,
            p.mother_name,
            p.phone,
            p.email,
            u.username
        FROM parents p
        JOIN users u
          ON u.id = p.user_id
        WHERE u.username = ?
          AND u.role = 'PARENT'
        LIMIT 1
        """,
        (username,)
    ).fetchone()


# ============================================================
# LIST STUDENTS
# ============================================================

@student_bp.get("")
@role_required("ADMIN")
def list_students():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                id,
                student_code,
                name,
                class_name,
                pickup_stop_id,
                drop_stop_id,
                bus_id,
                status,
                is_active,
                created_at
            FROM students
            WHERE is_active = 1
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()

        students = [
            get_student_dict(
                connection,
                row
            )
            for row in rows
        ]

        return jsonify({
            "success": True,
            "students": students,
            "count": len(students),
        }), 200

    finally:
        connection.close()


# ============================================================
# GET ONE STUDENT
# ============================================================

@student_bp.get("/<int:student_id>")
@role_required("ADMIN")
def get_student(student_id):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                id,
                student_code,
                name,
                class_name,
                pickup_stop_id,
                drop_stop_id,
                bus_id,
                status,
                is_active,
                created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,)
        ).fetchone()

        if not row:

            return jsonify({
                "success": False,
                "message": "Student not found.",
            }), 404

        return jsonify({
            "success": True,
            "student": get_student_dict(
                connection,
                row
            ),
        }), 200

    finally:
        connection.close()


# ============================================================
# CREATE STUDENT
# ============================================================

@student_bp.post("")
@role_required("ADMIN")
def create_student():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name") or ""
    ).strip()

    class_name = str(
        data.get("class_name") or ""
    ).strip()

    father_name = str(
        data.get("father_name") or ""
    ).strip()

    mother_name = str(
        data.get("mother_name") or ""
    ).strip()

    parent_username = str(
        data.get("parent_username") or ""
    ).strip()

    phone = str(
        data.get("phone") or ""
    ).strip()

    email = str(
        data.get("email") or ""
    ).strip()

    if not name:

        return jsonify({
            "success": False,
            "message": "Student name is required.",
        }), 400

    if not class_name:

        return jsonify({
            "success": False,
            "message": "Class is required.",
        }), 400

    if (
        not father_name
        and not mother_name
        and not parent_username
    ):

        return jsonify({
            "success": False,
            "message": (
                "Enter at least one parent name "
                "or an existing Parent ID."
            ),
        }), 400

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # Resolve existing or create new family account
        # ----------------------------------------------------

        parent = None
        temporary_password = None
        parent_created = False

        if parent_username:

            parent = find_parent_by_username(
                connection,
                parent_username
            )

            if not parent:

                return jsonify({
                    "success": False,
                    "message": (
                        f"Parent ID '{parent_username}' "
                        "was not found."
                    ),
                }), 404

            # Update supplied family information without
            # destroying existing values.
            connection.execute(
                """
                UPDATE parents
                SET
                    father_name =
                        CASE
                            WHEN ? <> '' THEN ?
                            ELSE father_name
                        END,
                    mother_name =
                        CASE
                            WHEN ? <> '' THEN ?
                            ELSE mother_name
                        END,
                    phone =
                        CASE
                            WHEN ? <> '' THEN ?
                            ELSE phone
                        END,
                    email =
                        CASE
                            WHEN ? <> '' THEN ?
                            ELSE email
                        END
                WHERE id = ?
                """,
                (
                    father_name,
                    father_name,
                    mother_name,
                    mother_name,
                    phone,
                    phone,
                    email,
                    email,
                    parent["id"],
                )
            )

        else:

            parent_username = generate_parent_username(
                connection
            )

            temporary_password = (
                generate_temporary_password()
            )

            parent_name = (
                father_name
                or mother_name
                or "Parent"
            )

            user_cursor = connection.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    role,
                    is_active
                )
                VALUES (?, ?, 'PARENT', 1)
                """,
                (
                    parent_username,
                    generate_password_hash(
                        temporary_password
                    ),
                )
            )

            user_id = user_cursor.lastrowid

            parent_cursor = connection.execute(
                """
                INSERT INTO parents (
                    user_id,
                    name,
                    father_name,
                    mother_name,
                    phone,
                    email
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    parent_name,
                    father_name or None,
                    mother_name or None,
                    phone or None,
                    email or None,
                )
            )

            parent_id = parent_cursor.lastrowid

            parent = {
                "id": parent_id,
                "user_id": user_id,
                "username": parent_username,
                "name": parent_name,
                "father_name": father_name,
                "mother_name": mother_name,
                "phone": phone,
                "email": email,
            }

            parent_created = True

        # ----------------------------------------------------
        # Create student
        # ----------------------------------------------------

        student_code = generate_student_code(
            connection
        )

        student_cursor = connection.execute(
            """
            INSERT INTO students (
                student_code,
                name,
                class_name,
                is_active,
                status
            )
            VALUES (?, ?, ?, 1, 'ACTIVE')
            """,
            (
                student_code,
                name,
                class_name,
            )
        )

        student_id = student_cursor.lastrowid

        # ----------------------------------------------------
        # Link student to family
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO student_parents (
                student_id,
                parent_id,
                relationship,
                is_primary
            )
            VALUES (?, ?, ?, 1)
            """,
            (
                student_id,
                parent["id"],
                "FAMILY",
            )
        )

        connection.commit()

        student_row = connection.execute(
            """
            SELECT
                id,
                student_code,
                name,
                class_name,
                pickup_stop_id,
                drop_stop_id,
                bus_id,
                status,
                is_active,
                created_at
            FROM students
            WHERE id = ?
            """,
            (student_id,)
        ).fetchone()

        return jsonify({
            "success": True,
            "message": (
                "Student created successfully."
            ),
            "student": get_student_dict(
                connection,
                student_row
            ),
            "parent": {
                **parent,
                "temporary_password":
                    temporary_password,
                    "created": parent_created,
            },
            "next_step": {
                "student_id": student_id,
                "action":
                    "REGISTER_FACE",
            },
        }), 201

    except Exception as error:

        connection.rollback()

        print(
            "Create student error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to create student."
            ),
            "error": str(error),
        }), 500

    finally:
        connection.close()


# ============================================================
# PERMANENT DELETE STUDENT
# ============================================================

@student_bp.delete("/<int:student_id>")
@role_required("ADMIN")
def delete_student(student_id):

    connection = get_connection()

    try:

        student = connection.execute(
            """
            SELECT
                id,
                student_code,
                name
            FROM students
            WHERE id = ?
            """,
            (student_id,)
        ).fetchone()

        if not student:

            return jsonify({
                "success": False,
                "message": "Student not found.",
            }), 404

        student_code = student["student_code"]
        student_name = student["name"]

        # Save face-file candidates before deleting DB data.
        uploads_directory = (
            Path(__file__).resolve().parent
            / "uploads"
            / "faces"
        )

        face_files = []

        for extension in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        ):

            file_path = (
                uploads_directory
                / f"{student_code}{extension}"
            )

            if file_path.exists():
                face_files.append(file_path)

        # ----------------------------------------------------
        # IMPORTANT:
        # The students table is referenced by
        # student_parents, face_embeddings, attendance,
        # travel_status and notifications with ON DELETE
        # CASCADE in the current database schema.
        #
        # Therefore this DELETE permanently removes the
        # student-specific records but does NOT delete the
        # parent account.
        # ----------------------------------------------------

        cursor = connection.execute(
            """
            DELETE FROM students
            WHERE id = ?
            """,
            (student_id,)
        )

        if cursor.rowcount != 1:

            connection.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Student could not be deleted."
                ),
            }), 404

        connection.commit()

        # ----------------------------------------------------
        # Remove physical face image(s)
        # ----------------------------------------------------

        deleted_face_files = 0

        for file_path in face_files:

            try:

                file_path.unlink()
                deleted_face_files += 1

            except OSError as file_error:

                # Database deletion remains successful.
                print(
                    "Warning: unable to delete face image "
                    f"{file_path}: {file_error}"
                )

        return jsonify({
            "success": True,
            "message": (
                f"Student {student_name} "
                f"({student_code}) was permanently deleted."
            ),
            "student": {
                "id": student_id,
                "student_code": student_code,
                "name": student_name,
            },
            "deleted_face_files":
                deleted_face_files,
        }), 200

    except Exception as error:

        connection.rollback()

        print(
            "Permanent student deletion error:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Unable to permanently delete "
                "the student."
            ),
            "error": str(error),
        }), 500

    finally:
        connection.close()
