from flask import Blueprint, request, jsonify, g
from auth import token_required
from database import get_connection
from insightface.app import FaceAnalysis

import numpy as np
import base64
import cv2


face_bp = Blueprint(
    "face",
    __name__,
    url_prefix="/api/face"
)


# ============================================================
# INSIGHTFACE MODEL
# ============================================================

face_app = None


def get_face_app():
    global face_app
    if face_app is None:
        face_app = FaceAnalysis(name="buffalo_l")
        face_app.prepare(ctx_id=0, det_size=(640, 640))
    return face_app


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(embedding1, embedding2):

    embedding1 = np.asarray(
        embedding1,
        dtype=np.float32
    )

    embedding2 = np.asarray(
        embedding2,
        dtype=np.float32
    )

    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(
        np.dot(embedding1, embedding2)
        / (norm1 * norm2)
    )


# ============================================================
# DECODE IMAGE
# ============================================================

def decode_image(image_data):

    if "," in image_data:

        image_data = image_data.split(
            ",",
            1
        )[1]

    image_bytes = base64.b64decode(
        image_data,
        validate=True
    )

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    return frame


# ============================================================
# RESIZE FOR FACE INFERENCE
# ============================================================

def resize_for_inference(frame, max_width=640):
    """Reduce oversized browser frames before InsightFace inference."""
    height, width = frame.shape[:2]

    if width <= max_width:
        return frame

    scale = max_width / float(width)
    new_size = (max_width, int(height * scale))

    return cv2.resize(
        frame,
        new_size,
        interpolation=cv2.INTER_AREA
    )


# ============================================================
# FACE DETECTION
# ============================================================

@face_bp.post("/detect")
@token_required
def detect_faces():

    data = request.get_json() or {}

    image_data = data.get("image")

    if not image_data:

        return jsonify({
            "success": False,
            "message": "Image is required"
        }), 400


    try:

        frame = decode_image(
            image_data
        )


        if frame is None:

            return jsonify({
                "success": False,
                "message": "Unable to decode image"
            }), 400


        inference_frame = resize_for_inference(frame)

        faces = get_face_app().get(
            inference_frame
        )


        detected_faces = []


        for face in faces:

            bbox = face.bbox.astype(
                int
            ).tolist()


            x1 = bbox[0]
            y1 = bbox[1]
            x2 = bbox[2]
            y2 = bbox[3]


            detected_faces.append({

                "x": x1,

                "y": y1,

                "width": x2 - x1,

                "height": y2 - y1,

                "confidence":
                    float(face.det_score)

            })


        return jsonify({

            "success": True,

            "face_count":
                len(detected_faces),

            "faces":
                detected_faces,

            "image_width":
                int(inference_frame.shape[1]),

            "image_height":
                int(inference_frame.shape[0])

        }), 200


    except Exception as error:

        print(
            "Face detection error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "Face detection failed",

            "error":
                str(error)

        }), 500


# ============================================================
# FACE RECOGNITION
# ============================================================

@face_bp.post("/recognize")
@token_required
def recognize_face():

    data = request.get_json() or {}

    image_data = data.get("image")


    if not image_data:

        return jsonify({

            "success": False,

            "message":
                "Image is required"

        }), 400


    connection = get_connection()


    try:

        # ----------------------------------------------------
        # Decode camera image
        # ----------------------------------------------------

        frame = decode_image(
            image_data
        )


        if frame is None:

            return jsonify({

                "success": False,

                "message":
                    "Unable to decode image"

            }), 400


        # ----------------------------------------------------
        # Detect faces
        # ----------------------------------------------------

        inference_frame = resize_for_inference(frame)

        faces = get_face_app().get(
            inference_frame
        )


        if len(faces) == 0:

            return jsonify({

                "success": True,

                "recognized": False,

                "message":
                    "No face detected",

                "faces": []

            }), 200


        # ----------------------------------------------------
        # Load registered embeddings
        # ----------------------------------------------------

        rows = connection.execute(
            """
            SELECT
                fe.id,
                fe.student_id,
                fe.embedding,
                fe.model_name,
                fe.model_version,
                s.student_code,
                s.name
            FROM face_embeddings fe
            INNER JOIN students s
                ON s.id = fe.student_id
            WHERE fe.is_active = 1
              AND s.is_active = 1
            """
        ).fetchall()


        if not rows:

            return jsonify({

                "success": True,

                "recognized": False,

                "message":
                    "No registered faces found",

                "faces": []

            }), 200


        # ----------------------------------------------------
        # Recognition threshold
        # ----------------------------------------------------

        RECOGNITION_THRESHOLD = 0.45


        recognized_faces = []


        # ----------------------------------------------------
        # Compare every detected face
        # ----------------------------------------------------

        for face in faces:

            current_embedding = (
                np.asarray(
                    face.embedding,
                    dtype=np.float32
                )
            )


            best_student = None

            best_similarity = -1.0


            # ------------------------------------------------
            # Compare with database embeddings
            # ------------------------------------------------

            for row in rows:

                stored_embedding = (
                    np.frombuffer(
                        row["embedding"],
                        dtype=np.float32
                    )
                )


                if (
                    stored_embedding.shape
                    != current_embedding.shape
                ):

                    continue


                similarity = cosine_similarity(
                    current_embedding,
                    stored_embedding
                )


                if similarity > best_similarity:

                    best_similarity = similarity

                    best_student = row


            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

            bbox = face.bbox.astype(
                int
            ).tolist()


            x1 = bbox[0]
            y1 = bbox[1]
            x2 = bbox[2]
            y2 = bbox[3]


            # ------------------------------------------------
            # Determine recognition
            # ------------------------------------------------

            is_recognized = (
                best_student is not None
                and
                best_similarity >=
                RECOGNITION_THRESHOLD
            )


            if is_recognized:

                recognized_faces.append({

                    "recognized": True,

                    "student_id":
                        best_student["student_id"],

                    "student_code":
                        best_student["student_code"],

                    "name":
                        best_student["name"],

                    "similarity":
                        round(
                            best_similarity,
                            4
                        ),

                    "x": x1,

                    "y": y1,

                    "width":
                        x2 - x1,

                    "height":
                        y2 - y1,

                    "confidence":
                        float(face.det_score)

                })

            else:

                recognized_faces.append({

                    "recognized": False,

                    "student_id": None,

                    "student_code": None,

                    "name": "Unknown",

                    "similarity":
                        round(
                            best_similarity,
                            4
                        ),

                    "x": x1,

                    "y": y1,

                    "width":
                        x2 - x1,

                    "height":
                        y2 - y1,

                    "confidence":
                        float(face.det_score)

                })


        # ----------------------------------------------------
        # Overall recognition result
        # ----------------------------------------------------

        any_recognized = any(
            face["recognized"]
            for face in recognized_faces
        )


        return jsonify({

            "success": True,

            "recognized":
                any_recognized,

            "face_count":
                len(recognized_faces),

            "faces":
                recognized_faces,

            "threshold":
                RECOGNITION_THRESHOLD,

            "image_width":
                int(inference_frame.shape[1]),

            "image_height":
                int(inference_frame.shape[0])

        }), 200


    except Exception as error:

        print(
            "Face recognition error:",
            error
        )


        return jsonify({

            "success": False,

            "message":
                "Face recognition failed",

            "error":
                str(error)

        }), 500


    finally:

        connection.close()