import sys
import unittest

sys.path.insert(0, ".")

from werkzeug.security import check_password_hash

from app import app
from database import get_connection


class Phase4AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        connection = get_connection()
        cls.student_id = connection.execute(
            "SELECT id FROM students WHERE student_code LIKE 'P3-%-STUDENT' ORDER BY id DESC LIMIT 1"
        ).fetchone()["id"]
        cls.bus_id = connection.execute(
            "SELECT bus_id FROM students WHERE id = ?", (cls.student_id,)
        ).fetchone()["bus_id"]
        connection.close()

    def login(self, username, password):
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.get_json()["token"]}

    def test_password_hash_and_no_password_leak(self):
        connection = get_connection()
        user = connection.execute(
            "SELECT password_hash FROM users WHERE username = 'parent1'"
        ).fetchone()
        self.assertNotEqual(user["password_hash"], "Parent@123")
        self.assertTrue(check_password_hash(user["password_hash"], "Parent@123"))
        connection.close()

        response = self.client.get("/api/profile", headers=self.login("parent1", "Parent@123"))
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", body)
        self.assertNotIn("password_hash", body)

    def test_logout_revokes_token(self):
        headers = self.login("parent1", "Parent@123")
        self.assertEqual(self.client.post("/api/auth/logout", headers=headers).status_code, 200)
        response = self.client.get("/api/profile", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "TOKEN_REVOKED")

    def test_parent_cannot_access_another_parent_student(self):
        headers = self.login("parent2", "Parent@123")
        response = self.client.get(f"/api/students/{self.student_id}", headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_driver_cannot_access_unassigned_bus(self):
        headers = self.login("driver1", "Driver@123")
        response = self.client.get("/api/buses/1", headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_role_restrictions(self):
        parent = self.login("parent1", "Parent@123")
        driver = self.login("driver1", "Driver@123")
        self.assertEqual(self.client.get("/api/drivers", headers=parent).status_code, 403)
        self.assertEqual(self.client.post("/api/buses", json={}, headers=parent).status_code, 403)
        self.assertEqual(self.client.post("/api/buses", json={}, headers=driver).status_code, 403)


if __name__ == "__main__":
    unittest.main()