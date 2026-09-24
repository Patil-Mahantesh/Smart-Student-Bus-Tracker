from flask import Blueprint, request, jsonify
from database import get_connection
from auth import role_required

from insightface.app import FaceAnalysis

import numpy as np
import base64
import cv2
import os


face_registration_bp = Blueprint(
    "face_registration",
    __name__,
    url_prefix="/api/face-registration"
)


# ============================================================
# FACE IMAGE STORAGE
# ============================================================

FACE_IMAGE_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "uploads",
    "faces"
)

os.makedirs(FACE_IMAGE_FOLDER, exist_ok=True)


# ============================================================
# INSIGHTFACE MODEL
# ============================================================

face_app = None


def get_face_app():
    global face_app
    if face_app is None:
        face_app = FaceAnalysis(name="buffalo_l")
        face_app.prepare(ctx_id=-1, det_size=(640, 640))
    return face_app


# ============================================================
# REGISTER STUDENT FACE
# ============================================================

@face_registration_bp.post("/<int:student_id>")
@role_required("ADMIN")
def register_student_face(student_id):

    data = request.get_json() or {}

    image_data = data.get("image")

    if not image_data:
        return jsonify({
            "message": "Image is required"
        }), 400

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # Check student
        # ----------------------------------------------------

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
                "message": "Student not found"
            }), 404

        if not student["is_active"]:
            return jsonify({
                "message": "Student is inactive"
            }), 400


        # ----------------------------------------------------
        # Remove Base64 header
        # ----------------------------------------------------

        if "," in image_data:
            image_data = image_data.split(",", 1)[1]


        # ----------------------------------------------------
        # Decode image
        # ----------------------------------------------------

        image_bytes = base64.b64decode(image_data)

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )


        # ----------------------------------------------------
        # Convert to OpenCV image
        # ----------------------------------------------------

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return jsonify({
                "message": "Unable to decode image"
            }), 400


        # ----------------------------------------------------
        # Detect face
        # ----------------------------------------------------

        faces = get_face_app().get(frame)

        if len(faces) == 0:
            return jsonify({
                "message":
                    "No face detected. Please position your face clearly in front of the camera."
            }), 400

        if len(faces) > 1:
            return jsonify({
                "message":
                    "Multiple faces detected. Please keep only one person in front of the camera."
            }), 400


        face = faces[0]


        # ----------------------------------------------------
        # Get embedding
        # ----------------------------------------------------

        embedding = face.embedding

        if embedding is None:
            return jsonify({
                "message":
                    "Unable to generate face embedding"
            }), 400


        embedding = np.asarray(
            embedding,
            dtype=np.float32
        )


        # ----------------------------------------------------
        # Save face image
        # ----------------------------------------------------

        student_code = student["student_code"]

        image_filename = f"{student_code}.jpg"

        image_path = os.path.join(
            FACE_IMAGE_FOLDER,
            image_filename
        )

        success = cv2.imwrite(
            image_path,
            frame
        )

        if not success:
            return jsonify({
                "message":
                    "Unable to save face image"
            }), 500


        # ----------------------------------------------------
        # Disable previous active embeddings
        # ----------------------------------------------------

        connection.execute(
            """
            UPDATE face_embeddings
            SET
                is_active = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE student_id = ?
              AND is_active = 1
            """,
            (student_id,)
        )


        # ----------------------------------------------------
        # Store new embedding
        # ----------------------------------------------------

        connection.execute(
            """
            INSERT INTO face_embeddings
            (
                student_id,
                embedding,
                model_name,
                model_version,
                is_active
            )
            VALUES (?, ?, ?, ?, 1)
            """,
            (
                student_id,
                embedding.tobytes(),
                "InsightFace",
                "buffalo_l"
            )
        )


        connection.commit()


        # ----------------------------------------------------
        # Return success
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "message":
                "Student face registered successfully",

            "student": {

                "id":
                    student["id"],

                "student_code":
                    student["student_code"],

                "name":
                    student["name"]

            },

            "face": {

                "image":
                    f"uploads/faces/{image_filename}",

                "embedding_size":
                    int(len(embedding)),

                "model":
                    "buffalo_l"

            }

        }), 201


    except Exception as error:

        connection.rollback()

        print(
            "Face registration error:",
            error
        )

        return jsonify({

            "message":
                "Face registration failed",

            "error":
                str(error)

        }), 500


    finally:

        connection.close()