import os
import os
import math
import time
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

#download the model if it doesn't exist
if not os.path.exists(MODEL_PATH):
    print("Downloading face landmark model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

#stolen straight from the MediaPipe docs, sets up the face landmark model
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=vision.RunningMode.VIDEO,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=1,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

#remembered between frames (for blinks and head movement)
state = {"prev_pose": None, "eyes_closed": False, "blinks": 0}
TEXT_BRIGHTNESS_THRESHOLD = 127


def head_pose(matrix):
    r = matrix[:3, :3]
    r = r / (r[:, 0] ** 2).sum() ** 0.5  #remove scale

    pitch = math.atan2(r[2][1], r[2][2])
    yaw = math.atan2(-r[2][0], math.sqrt(r[2][1] ** 2 + r[2][2] ** 2))
    roll = math.atan2(r[1][0], r[0][0])

    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)


def analyze(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect_for_video(image, int(time.time() * 1000))

    if not result.face_landmarks:
        state["prev_pose"] = None
        return None, None

    #blendshapes are 0-1 scores like "jawOpen" or "eyeBlinkLeft"
    b = {c.category_name: c.score for c in result.face_blendshapes[0]}

    eye_openness = 1 - (b["eyeBlinkLeft"] + b["eyeBlinkRight"]) / 2
    mouth_openness = b["jawOpen"]
    brow_raise = (b["browInnerUp"] + b["browOuterUpLeft"] + b["browOuterUpRight"]) / 3
    smile = (b["mouthSmileLeft"] + b["mouthSmileRight"]) / 2

    gaze_x = (b["eyeLookOutRight"] + b["eyeLookInLeft"]
              - b["eyeLookOutLeft"] - b["eyeLookInRight"]) / 2
    gaze_y = (b["eyeLookUpLeft"] + b["eyeLookUpRight"]
              - b["eyeLookDownLeft"] - b["eyeLookDownRight"]) / 2

    #blink: count it once each time the eyes go from open to closed
    closed = eye_openness < 0.5
    if closed and not state["eyes_closed"]:
        state["blinks"] += 1
    state["eyes_closed"] = closed

    #head pose + how much it moved since the last frame
    yaw, pitch, roll = head_pose(result.facial_transformation_matrixes[0])
    pose = (yaw, pitch, roll)

    if state["prev_pose"] is None:
        head_movement = 0
    else:
        head_movement = sum(abs(a - p) for a, p in zip(pose, state["prev_pose"]))
    state["prev_pose"] = pose

    features = {
        "eye_openness": round(eye_openness, 2),
        "mouth_openness": round(mouth_openness, 2),
        "brow_raise": round(brow_raise, 2),
        "smile": round(smile, 2),
        "blink": int(closed),
        "blink_count": state["blinks"],
        "head_yaw": round(yaw, 1),
        "head_pitch": round(-pitch, 1),
        "head_roll": round(-roll, 1),
        "head_movement": round(head_movement, 2),
        "gaze_x": round(gaze_x, 2),
        "gaze_y": round(gaze_y, 2),
    }

    return features, result.face_landmarks[0]


def _text_color(gray_frame, text, origin, font, scale, thickness):
    text_width, text_height = cv2.getTextSize(
        text, font, scale, thickness
    )[0]
    x, y = origin
    h, w = gray_frame.shape
    background = gray_frame[
        max(0, y - text_height):min(h, y),
        max(0, x):min(w, x + text_width),
    ]

    if background.size and background.mean() < TEXT_BRIGHTNESS_THRESHOLD:
        return (255, 255, 255)
    return (0, 0, 0)


def draw(frame, features, landmarks):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if features is None:
        text = "No face found"
        color = _text_color(
            gray_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
        )
        cv2.putText(frame, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return

    h, w = frame.shape[:2]
    for point in landmarks:
        cv2.circle(frame, (int(point.x * w), int(point.y * h)), 1, (0, 255, 0), -1)

    y = 25
    for name, value in features.items():
        text = f"{name}: {value}"
        color = _text_color(
            gray_frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        cv2.putText(frame, text, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        y += 20