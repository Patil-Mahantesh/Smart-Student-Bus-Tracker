from flask import Flask, jsonify
from flask_cors import CORS

from auth_routes import auth_bp
from student_routes import student_bp
from parent_routes import parent_bp
from driver_routes import driver_bp
from bus_routes import bus_bp
from route_routes import route_bp
from travel_routes import travel_bp
from trip_routes import trip_bp
from face_routes import face_bp
from face_registration_routes import face_registration_bp
from attendance_routes import attendance_bp
from notification_routes import notification_bp
from location_routes import location_bp
from core_routes import core_bp
from stop_routes import stop_bp

from database import get_connection, initialize_database
from config import Config


app = Flask(__name__)

# Initialize and migrate the configured database.
initialize_database()

# Restrict cross-origin requests to configured frontend origins.
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS
        }
    }
)


# =========================================================
# REGISTER API ROUTES
# =========================================================

app.register_blueprint(student_bp)
app.register_blueprint(parent_bp)
app.register_blueprint(driver_bp)
app.register_blueprint(bus_bp)
app.register_blueprint(route_bp)
app.register_blueprint(travel_bp)
app.register_blueprint(trip_bp)
app.register_blueprint(face_bp)
app.register_blueprint(face_registration_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(location_bp)
app.register_blueprint(core_bp)
app.register_blueprint(stop_bp)
app.register_blueprint(auth_bp)


# =========================================================
# HEALTH CHECKS
# =========================================================

@app.get("/")
def home():
    return jsonify({
        "success": True,
        "message": "Smart Student Bus Tracker backend is running"
    })


@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Backend is healthy"
    })


@app.get("/health")
def health_compatibility():
    # Retain the existing compatibility endpoint.
    return health()


@app.get("/api/db-test")
def database_test():
    connection = get_connection()

    try:
        table_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchone()["count"]

        return jsonify({
            "success": True,
            "table_count": table_count
        })

    finally:
        connection.close()


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    print()
    print("==============================================")
    print(" SMART STUDENT BUS TRACKER BACKEND")
    print("==============================================")
    print(" Server: http://127.0.0.1:5000")
    print(" Debug mode: disabled")
    print("==============================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
