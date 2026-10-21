
import os

from werkzeug.security import generate_password_hash
from database import get_connection


def bootstrap_production_accounts():
    """Create configured accounts and missing profiles without resetting passwords."""

    accounts = [
        {
            "role": "ADMIN",
            "username": os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip(),
            "password": os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""),
            "name": os.getenv("BOOTSTRAP_ADMIN_NAME", "System Administrator").strip(),
            "profile_table": "admins",
            "profile_fields": ("name",),
            "profile_values": lambda: (
                os.getenv("BOOTSTRAP_ADMIN_NAME", "System Administrator").strip(),
            ),
        },
        {
            "role": "DRIVER",
            "username": os.getenv("BOOTSTRAP_DRIVER_USERNAME", "").strip(),
            "password": os.getenv("BOOTSTRAP_DRIVER_PASSWORD", ""),
            "name": os.getenv("BOOTSTRAP_DRIVER_NAME", "").strip(),
            "profile_table": "drivers",
            "profile_fields": ("name", "phone", "license_number"),
            "profile_values": lambda: (
                os.getenv("BOOTSTRAP_DRIVER_NAME", "").strip(),
                os.getenv("BOOTSTRAP_DRIVER_PHONE", "").strip() or None,
                os.getenv("BOOTSTRAP_DRIVER_LICENSE", "").strip() or None,
            ),
        },
        {
            "role": "PARENT",
            "username": os.getenv("BOOTSTRAP_PARENT_USERNAME", "").strip(),
            "password": os.getenv("BOOTSTRAP_PARENT_PASSWORD", ""),
            "name": os.getenv("BOOTSTRAP_PARENT_NAME", "").strip(),
            "profile_table": "parents",
            "profile_fields": ("name", "phone", "email"),
            "profile_values": lambda: (
                os.getenv("BOOTSTRAP_PARENT_NAME", "").strip(),
                os.getenv("BOOTSTRAP_PARENT_PHONE", "").strip() or None,
                os.getenv("BOOTSTRAP_PARENT_EMAIL", "").strip() or None,
            ),
        },
    ]

    for account in accounts:
        if not account["username"] or not account["password"] or not account["name"]:
            raise RuntimeError(
                f"Missing username, password, or name for {account['role']} "
                "bootstrap account. Configure the BOOTSTRAP_* environment variables."
            )

        if len(account["password"]) < 16:
            raise RuntimeError(
                f"The configured {account['role']} bootstrap password "
                "must be at least 16 characters."
            )

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        for account in accounts:
            user = connection.execute(
                "SELECT id, role FROM users WHERE username = ?",
                (account["username"],),
            ).fetchone()

            if user:
                if user["role"] != account["role"]:
                    raise RuntimeError(
                        f"Username '{account['username']}' already exists "
                        "with a different role. Choose another configured username."
                    )
                user_id = user["id"]
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?, ?, ?)
                    """,
                    (
                        account["username"],
                        generate_password_hash(account["password"]),
                        account["role"],
                    ),
                )
                user_id = cursor.lastrowid

            profile = connection.execute(
                f"SELECT id FROM {account['profile_table']} WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if not profile:
                fields = ("user_id",) + account["profile_fields"]
                placeholders = ", ".join("?" for _ in fields)
                columns = ", ".join(fields)
                values = (user_id,) + account["profile_values"]()

                connection.execute(
                    f"INSERT INTO {account['profile_table']} ({columns}) "
                    f"VALUES ({placeholders})",
                    values,
                )

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
