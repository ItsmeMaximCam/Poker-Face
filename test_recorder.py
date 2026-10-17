import os
import time

os.environ["POKER_DB"] = ":memory:"

import recorder
from cards import new_deck, draw

deck = new_deck()
player_cards = draw(deck, 2)
ai_cards = draw(deck, 2)
board = draw(deck, 5)

recorder.start_hand()
hand_id = recorder.current["hand_id"]

#hole cards must not be stored while the hand is running
row = recorder.db.execute("SELECT player_cards FROM hands WHERE id = ?", (hand_id,)).fetchone()
assert row[0] is None

fake_face = {name: 0.5 for name in recorder.FEATURES}
recorder.save_sample(time.time(), hand_id, "Preflop", fake_face)
recorder.new_street("Flop")
recorder.save_sample(time.time(), hand_id, "Flop", None)  #no face found
recorder.record_event("player_action", "raise", 20, 1.5)
recorder.record_event("ai_action", "call", 20)
recorder.end_hand(player_cards, ai_cards, board, "player", "showdown")

db = recorder.db
events = db.execute("SELECT event, street, hand_id FROM events ORDER BY id").fetchall()
assert [e[0] for e in events] == ["hand_start", "street_revealed", "player_action", "ai_action", "hand_end"]
assert all(e[2] == hand_id for e in events)
assert events[1][1] == "Flop"

samples = db.execute("SELECT face_found, eye_openness, hand_id FROM face_samples ORDER BY id").fetchall()
assert samples[0] == (1, 0.5, hand_id)
assert samples[1] == (0, None, hand_id)  #missing face is NULL, not 0

hand = db.execute("SELECT player_cards, player_category, winner FROM hands WHERE id = ?", (hand_id,)).fetchone()
assert hand[0] is not None and hand[1] is not None and hand[2] == "player"

decision = db.execute("SELECT decision_time FROM events WHERE event = 'player_action'").fetchone()
assert decision[0] == 1.5

print("All good. Hand", hand_id, "->", hand)