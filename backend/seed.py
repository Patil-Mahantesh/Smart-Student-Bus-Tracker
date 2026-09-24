from werkzeug.security import generate_password_hash

from database import get_connection, initialize_database


def _user(connection, username, password, role):
    row = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return row["id"]
    cursor = connection.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), role),
    )
    return cursor.lastrowid


def seed_development_data():
    """Create identifiable local development identities without biometric data."""
    initialize_database()
    connection = get_connection()
    try:
        admin_id = _user(connection, "admin", "Admin@123", "ADMIN")
        parent_user_id = _user(connection, "parent1", "Parent@123", "PARENT")
        driver_user_id = _user(connection, "driver1", "Driver@123", "DRIVER")
        connection.execute("INSERT OR IGNORE INTO admins (user_id, name) VALUES (?, ?)", (admin_id, "Development Admin"))
        connection.execute("INSERT OR IGNORE INTO parents (user_id, name, phone, email) VALUES (?, ?, ?, ?)", (parent_user_id, "Development Parent", "9000000001", "parent1@example.com"))
        connection.execute("INSERT OR IGNORE INTO drivers (user_id, name, phone, license_number, employee_id) VALUES (?, ?, ?, ?, ?)", (driver_user_id, "Development Driver", "9000000002", "DEV-LICENSE-001", "DEV-DRIVER-001"))
        connection.execute("UPDATE drivers SET employee_id = COALESCE(employee_id, 'DEV-DRIVER-001') WHERE user_id = ?", (driver_user_id,))
        connection.commit()
        print("Development identities are ready. No face encodings were created.")
    finally:
        connection.close()


if __name__ == "__main__":
    seed_development_data()