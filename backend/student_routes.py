from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

import secrets
import string

from auth import role_required
from database import get_connection


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/api/students"
)


# ============================================================
# GENERATE NEXT UNUSED STUDENT CODE
# ============================================================

def generate_student_code(connection):
    """
    Generate the next unused student code.

    Examples:
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

    used_numbers = set()

    for row in rows:
        code = row["student_code"]

        if not code:
            continue

        suffix = code[3:]

        if suffix.isdigit():
            used_numbers.add(int(suffix))

    number = 1

    while number in used_numbers:
        number += 1

    return f"STU{number:03d}"


# ============================================================
# GENERATE NEXT FAMILY/PARENT USERNAME
# ============================================================

def generate_parent_username(connection):
    """
    Generate the next unused family username.

    Examples:
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

    highest_number = 0

    for row in rows:
        username = row["username"]

        if not username:
            continue

        suffix = username[6:]

        if suffix.isdigit():
            highest_number = max(
                highest_number,
                int(suffix)
            )

    return f"parent{highest_number + 1:05d}"


# ============================================================
# GENERATE TEMPORARY PASSWORD
# ============================================================

def generate_temporary_password(length=10):
    characters = (
        string.ascii_letters
        + string.digits
        + "!@#$"
    )

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


# ============================================================
# GET FAMILY DETAILS
# ============================================================

def get_parent_details(connection, parent_id):

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
            u.username,
            u.is_active

        FROM parents p

        INNER JOIN users u
            ON u.id = p.user_id

        WHERE p.id = ?
        """,
        (parent_id,)
    ).fetchone()

    if not row:
        return None

    return dict(row)


# ============================================================
# CREATE STUDENT
# ============================================================

@student_bp.post("")
@role_required("ADMIN")
def create_student():

    data = request.get_json(silent=True) or {}

    student_name = str(
        data.get("name", "")
    ).strip()

    class_name = str(
        data.get("class_name", "")
    ).strip()

    father_name = str(
        data.get("father_name", "")
    ).strip()

    mother_name = str(
        data.get("mother_name", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip()

    # Optional:
    # If supplied, this student will be linked
    # to an existing family account.
    existing_parent_username = str(
        data.get("parent_username", "")
    ).strip()

    # Password is created by the Admin.
    parent_password = str(
        data.get("parent_password", "")
    ).strip()

    # ========================================================
    # VALIDATION
    # ========================================================

    if not student_name:
        return jsonify({
            "success": False,
            "message": "Student name is required."
        }), 400

    if not class_name:
        return jsonify({
            "success": False,
            "message": "Class is required."
        }), 400

    if not parent_password:
        return jsonify({
            "success": False,
            "message": "Parent password is required."
        }), 400

    if len(parent_password) < 6:
        return jsonify({
            "success": False,
            "message": "Parent password must be at least 6 characters."
        }), 400

    # New family requires at least one parent.
    if (
        not father_name
        and not mother_name
        and not existing_parent_username
    ):
        return jsonify({
            "success": False,
            "message": (
                "At least one parent detail is required. "
                "Enter father name or mother name."
            )
        }), 400

    connection = get_connection()

    try:

        # ====================================================
        # CREATE STUDENT
        # ====================================================

        student_code = generate_student_code(
            connection
        )

        cursor = connection.execute(
            """
            INSERT INTO students (
                student_code,
                name,
                class_name,
                is_active
            )
            VALUES (?, ?, ?, 1)
            """,
            (
                student_code,
                student_name,
                class_name
            )
        )

        student_id = cursor.lastrowid

        # ====================================================
        # EXISTING FAMILY
        # ====================================================

        if existing_parent_username:

            parent_row = connection.execute(
                """
                SELECT
                    p.id,
                    p.user_id,
                    p.name,
                    p.father_name,
                    p.mother_name,
                    p.phone,
                    p.email,
                    u.username,
                    u.is_active

                FROM parents p

                INNER JOIN users u
                    ON u.id = p.user_id

                WHERE u.username = ?
                  AND u.role = 'PARENT'
                """,
                (existing_parent_username,)
            ).fetchone()

            if not parent_row:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message": (
                        "The specified family account "
                        "was not found."
                    )
                }), 404

            parent_id = parent_row["id"]

            # Admin-created password replaces the existing
            # password for this parent account.
            new_password_hash = generate_password_hash(
                parent_password
            )

            connection.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                  AND role = 'PARENT'
                """,
                (
                    new_password_hash,
                    parent_row["user_id"]
                )
            )

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
                    parent_id,
                    "FAMILY"
                )
            )

            connection.commit()

            return jsonify({
                "success": True,

                "message": (
                    "Student created and linked to "
                    "the existing family account. "
                    "Proceed to face registration."
                ),

                "student": {
                    "id": student_id,
                    "student_code": student_code,
                    "name": student_name,
                    "class_name": class_name
                },

                "parent": {
                    "id": parent_id,
                    "username": parent_row["username"],
                    "password": parent_password,
                    "temporary_password": None,
                    "father_name": parent_row["father_name"],
                    "mother_name": parent_row["mother_name"]
                },

                "next_step": {
                    "action": "FACE_REGISTRATION",
                    "student_id": student_id
                }
            }), 201

        # ====================================================
        # CREATE NEW FAMILY ACCOUNT
        # ====================================================

        parent_username = generate_parent_username(
            connection
        )

        password_hash = generate_password_hash(
            parent_password
        )

        # Family display name.
        if father_name and mother_name:
            family_name = (
                f"{father_name} & {mother_name}"
            )
        elif father_name:
            family_name = father_name
        else:
            family_name = mother_name

        # ====================================================
        # CREATE USER
        # ====================================================

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
                password_hash
            )
        )

        user_id = user_cursor.lastrowid

        # ====================================================
        # CREATE FAMILY/PARENT RECORD
        # ====================================================

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
                family_name,
                father_name or None,
                mother_name or None,
                phone or None,
                email or None
            )
        )

        parent_id = parent_cursor.lastrowid

        # ====================================================
        # LINK STUDENT TO FAMILY
        # ====================================================

        if father_name and mother_name:
            relationship = "FATHER_MOTHER"
        elif father_name:
            relationship = "FATHER"
        else:
            relationship = "MOTHER"

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
                parent_id,
                relationship
            )
        )

        connection.commit()

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({
            "success": True,

            "message": (
                "Student created successfully. "
                "Proceed to face registration."
            ),

            "student": {
                "id": student_id,
                "student_code": student_code,
                "name": student_name,
                "class_name": class_name
            },

            "parent": {
                "id": parent_id,
                "username": parent_username,
                "password": parent_password,
                "temporary_password": None,
                "father_name": father_name or None,
                "mother_name": mother_name or None
            },

            "next_step": {
                "action": "FACE_REGISTRATION",
                "student_id": student_id
            }
        }), 201

    except Exception as error:

        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to create student.",
            "error": str(error)
        }), 500

    finally:
        connection.close()


# ============================================================
# GET ALL STUDENTS
# ============================================================

@student_bp.get("")
@role_required("ADMIN")
def get_students():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                s.id,
                s.student_code,
                s.name,
                s.class_name,
                s.bus_id,
                s.status,
                s.is_active,
                s.created_at,

                p.id AS parent_id,
                u.username AS parent_username,
                p.father_name,
                p.mother_name,

                CASE
                    WHEN fe.id IS NOT NULL
                    THEN 1
                    ELSE 0
                END AS has_face

            FROM students s

            LEFT JOIN student_parents sp
                ON sp.student_id = s.id
                AND sp.is_primary = 1

            LEFT JOIN parents p
                ON p.id = sp.parent_id

            LEFT JOIN users u
                ON u.id = p.user_id

            LEFT JOIN face_embeddings fe
                ON fe.student_id = s.id
                AND fe.is_active = 1

            WHERE s.is_active = 1

            ORDER BY s.id DESC
            """
        ).fetchall()

        students = []

        for row in rows:

            students.append({
                "id": row["id"],
                "student_code": row["student_code"],
                "name": row["name"],
                "class_name": row["class_name"],
                "bus_id": row["bus_id"],
                "status": row["status"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],

                "parent": {
                    "id": row["parent_id"],
                    "username": row["parent_username"],
                    "father_name": row["father_name"],
                    "mother_name": row["mother_name"]
                },

                "has_face": bool(row["has_face"])
            })

        return jsonify({
            "success": True,
            "students": students,
            "count": len(students)
        })

    finally:
        connection.close()


# ============================================================
# GET SINGLE STUDENT
# ============================================================

@student_bp.get("/<int:student_id>")
@role_required("ADMIN")
def get_student(student_id):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT
                s.id,
                s.student_code,
                s.name,
                s.class_name,
                s.bus_id,
                s.status,
                s.is_active,
                s.created_at,

                p.id AS parent_id,
                u.username AS parent_username,
                p.name AS family_name,
                p.father_name,
                p.mother_name,
                p.phone,
                p.email

            FROM students s

            LEFT JOIN student_parents sp
                ON sp.student_id = s.id
                AND sp.is_primary = 1

            LEFT JOIN parents p
                ON p.id = sp.parent_id

            LEFT JOIN users u
                ON u.id = p.user_id

            WHERE s.id = ?
            """,
            (student_id,)
        ).fetchone()

        if not row:
            return jsonify({
                "success": False,
                "message": "Student not found."
            }), 404

        face = connection.execute(
            """
            SELECT
                id,
                model_name,
                model_version,
                created_at,
                updated_at

            FROM face_embeddings

            WHERE student_id = ?
              AND is_active = 1

            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id,)
        ).fetchone()

        return jsonify({
            "success": True,

            "student": {
                "id": row["id"],
                "student_code": row["student_code"],
                "name": row["name"],
                "class_name": row["class_name"],
                "bus_id": row["bus_id"],
                "status": row["status"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"]
            },

            "parent": {
                "id": row["parent_id"],
                "username": row["parent_username"],
                "family_name": row["family_name"],
                "father_name": row["father_name"],
                "mother_name": row["mother_name"],
                "phone": row["phone"],
                "email": row["email"]
            },

            "face": (
                {
                    "registered": True,
                    "id": face["id"],
                    "model_name": face["model_name"],
                    "model_version": face["model_version"],
                    "created_at": face["created_at"],
                    "updated_at": face["updated_at"]
                }
                if face
                else {
                    "registered": False
                }
            )
        })

    finally:
        connection.close()


# ============================================================
# GET STUDENTS FOR A FAMILY
# ============================================================

@student_bp.get("/parent/<int:parent_id>")
@role_required("ADMIN")
def get_parent_students(parent_id):

    connection = get_connection()

    try:

        parent = get_parent_details(
            connection,
            parent_id
        )

        if not parent:
            return jsonify({
                "success": False,
                "message": "Parent/family account not found."
            }), 404

        rows = connection.execute(
            """
            SELECT
                s.id,
                s.student_code,
                s.name,
                s.class_name,
                sp.relationship,
                sp.is_primary

            FROM students s

            INNER JOIN student_parents sp
                ON sp.student_id = s.id

            WHERE sp.parent_id = ?

            ORDER BY s.id
            """,
            (parent_id,)
        ).fetchall()

        students = [
            {
                "id": row["id"],
                "student_code": row["student_code"],
                "name": row["name"],
                "class_name": row["class_name"],
                "relationship": row["relationship"],
                "is_primary": bool(row["is_primary"])
            }
            for row in rows
        ]

        return jsonify({
            "success": True,
            "parent": parent,
            "students": students
        })

    finally:
        connection.close()


# ============================================================
# DELETE / DEACTIVATE STUDENT
# ============================================================

@student_bp.delete("/<int:student_id>")
@role_required("ADMIN")
def delete_student(student_id):
    """
    Soft-delete a student.

    The student record is preserved so historical attendance,
    notifications, reports, and relationships remain available.
    The student is simply marked inactive.

    The associated family/parent account is NOT deleted because
    the same family may have other children.
    """

    connection = get_connection()

    try:
        student = connection.execute(
            """
            SELECT
                id,
                student_code,
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
                "message": "Student not found."
            }), 404

        if not student["is_active"]:
            return jsonify({
                "success": False,
                "message": "Student is already inactive."
            }), 409

        # Deactivate the student.
        connection.execute(
            """
            UPDATE students
            SET is_active = 0
            WHERE id = ?
            """,
            (student_id,)
        )

        # Disable the student's active face embeddings.
        # This prevents the student from being recognized again,
        # while preserving the embedding history.
        connection.execute(
            """
            UPDATE face_embeddings
            SET is_active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE student_id = ?
              AND is_active = 1
            """,
            (student_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": (
                f"Student {student['name']} "
                f"({student['student_code']}) has been deactivated."
            ),
            "student": {
                "id": student["id"],
                "student_code": student["student_code"],
                "name": student["name"],
                "is_active": False
            }
        }), 200

    except Exception as error:
        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to deactivate student.",
            "error": str(error)
        }), 500

    finally:
        connection.close()
