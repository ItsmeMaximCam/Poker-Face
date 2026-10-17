import os
import time
import sqlite3
import threading
import cv2
from vision import analyze
from cards import evaluate, plain_cards


DB_PATH = os.environ.get("POKER_DB", "poker_face.db")
SAMPLE_INTERVAL = 0.1  #10 face samples per second

FEATURES = ["eye_openness", "mouth_openness", "brow_raise", "smile", "blink",
            "blink_count", "head_yaw", "head_pitch", "head_roll",
            "head_movement", "gaze_x", "gaze_y"]

#the camera thread and the game both write, so share one connection + a lock
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
lock = threading.Lock()

#shared between the game and the camera thread
current = {"hand_id": None, "street": None}

db.executescript("""
CREATE TABLE IF NOT EXISTS hands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time REAL,
    end_time REAL,
    ended_by TEXT,
    winner TEXT,
    player_cards TEXT,
    ai_cards TEXT,
    board TEXT,
    player_category TEXT,
    player_score INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hand_id INTEGER NOT NULL,
    t REAL,
    street TEXT,
    event TEXT,
    action TEXT,
    amount INTEGER,
    decision_time REAL
);

CREATE TABLE IF NOT EXISTS face_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hand_id INTEGER NOT NULL,
    t REAL,
    street TEXT,
    face_found INTEGER,
    eye_openness REAL,
    mouth_openness REAL,
    brow_raise REAL,
    smile REAL,
    blink INTEGER,
    blink_count INTEGER,
    head_yaw REAL,
    head_pitch REAL,
    head_roll REAL,
    head_movement REAL,
    gaze_x REAL,
    gaze_y REAL
);
""")


def start_hand():
    """No cards here on purpose, they're only attached in end_hand()."""
    t = time.time()
    with lock:
        cursor = db.execute("INSERT INTO hands (start_time) VALUES (?)", (t,))
        db.commit()
        current["hand_id"] = cursor.lastrowid
        current["street"] = "Preflop"
    record_event("hand_start", t=t)


def new_street(street):
    with lock:
        current["street"] = street
    record_event("street_revealed")


def record_event(event, action=None, amount=None, decision_time=None, t=None):
    if t is None:
        t = time.time()
    with lock:
        db.execute(
            "INSERT INTO events (hand_id, t, street, event, action, amount, decision_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (current["hand_id"], t, current["street"], event, action, amount, decision_time))
        db.commit()


def end_hand(player_cards, ai_cards, board, winner, ended_by):
    """Ground truth gets attached here, after the hand is over."""
    t = time.time()

    score, category = None, None
    if len(board) >= 3:  #can't evaluate a hand before the flop
        score, category = evaluate(player_cards, board)

    with lock:
        db.execute(
            "UPDATE hands SET end_time = ?, ended_by = ?, winner = ?, player_cards = ?, "
            "ai_cards = ?, board = ?, player_category = ?, player_score = ? WHERE id = ?",
            (t, ended_by, winner, plain_cards(player_cards), plain_cards(ai_cards),
             plain_cards(board), category, score, current["hand_id"]))
        db.commit()

    record_event("hand_end", t=t)

    with lock:
        current["hand_id"] = None
        current["street"] = None


def save_sample(t, hand_id, street, features):
    """features is None when no face was found, so every measurement is saved as NULL."""
    if features is None:
        values = [None] * len(FEATURES)
    else:
        values = [features[name] for name in FEATURES]

    marks = ", ".join("?" * (len(FEATURES) + 4))
    with lock:
        db.execute(
            f"INSERT INTO face_samples (hand_id, t, street, face_found, {', '.join(FEATURES)}) "
            f"VALUES ({marks})",
            [hand_id, t, street, int(features is not None)] + values)
        db.commit()


def camera_loop(cap):
    next_save = 0

    while True:
        ok, frame = cap.read()
        t = time.time()

        #analyze every frame so blink counting stays accurate, but only save 10/sec
        if ok:
            features, landmarks = analyze(cv2.flip(frame, 1))
        else:
            features = None
            time.sleep(0.05)

        if t < next_save:
            continue

        with lock:
            hand_id, street = current["hand_id"], current["street"]

        if hand_id is None:  #no hand in progress
            continue

        save_sample(t, hand_id, street, features)

        next_save += SAMPLE_INTERVAL
        if next_save < t:  #fell behind, don't try to catch up
            next_save = t + SAMPLE_INTERVAL


def start_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Couldn't open webcam. Face samples will be saved as unavailable.")
    threading.Thread(target=camera_loop, args=(cap,), daemon=True).start()