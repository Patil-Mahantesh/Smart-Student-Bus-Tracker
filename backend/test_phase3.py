import sys
import unittest

sys.path.insert(0, ".")

from app import app
from database import get_connection


class Phase3ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def token(self, username, password):
        response = self.client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.get_json()["token"]}

    def test_phase2_health_and_database(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        response = self.client.get("/api/db-test")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.get_json()["table_count"], 19)

    def test_role_authorization(self):
        response = self.client.post("/api/buses/", json={})
        self.assertEqual(response.status_code, 401)
        parent = self.token("parent1", "Parent@123")
        response = self.client.post("/api/buses/", json={}, headers=parent)
        self.assertEqual(response.status_code, 403)

    def test_core_schema_relationships_exist(self):
        connection = get_connection()
        try:
            for table in ("users", "parents", "students", "drivers", "buses", "routes", "stops", "trips", "attendance"):
                self.assertIsNotNone(connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone())
            self.assertIn("bus_id", {row["name"] for row in connection.execute("PRAGMA table_info(students)")})
            self.assertIn("attendance_date", {row["name"] for row in connection.execute("PRAGMA table_info(attendance)")})
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()