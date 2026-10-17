import sys
import sqlite3


db = sqlite3.connect("poker_face.db")

#Get the hand's id from command line
if len(sys.argv) > 1:
    hand_id = int(sys.argv[1])
else:
    hand_id = db.execute("SELECT MAX(id) FROM hands").fetchone()[0]

if hand_id is None:
    print("No hands recorded yet.")
    sys.exit()


start, end, ended_by, winner, player_cards, ai_cards, board, category = db.execute(
    "SELECT start_time, end_time, ended_by, winner, player_cards, ai_cards, board, "
    "player_category FROM hands WHERE id = ?", (hand_id,)).fetchone()

events = db.execute(
    "SELECT t, street, event, action, amount, decision_time FROM events "
    "WHERE hand_id = ? ORDER BY t, id", (hand_id,)).fetchall()
samples = db.execute(
    "SELECT t, face_found, eye_openness FROM face_samples "
    "WHERE hand_id = ? ORDER BY t", (hand_id,)).fetchall()

print(f"Hand {hand_id}: ended by {ended_by}, winner {winner}")
print(f"  You: {player_cards} ({category}) | AI: {ai_cards} | Board: {board}")

print("\nEvents (seconds since hand start) and the nearest face sample:")
for t, street, event, action, amount, decision_time in events:
    detail = f"{action or ''} {'' if amount is None else amount}".strip()
    thought = f" thought {decision_time:.2f}s" if decision_time else ""

    near = "no face samples"
    if samples:
        s = min(samples, key=lambda s: abs(s[0] - t))
        face = f"eye={s[2]}" if s[1] else "no face"
        near = f"nearest sample {s[0] - t:+.2f}s ({face})"

    print(f"{t - start:7.2f}s  {street or '':8} {event:15} {detail:10}{thought}  | {near}")

times = [s[0] for s in samples]
found = sum(s[1] for s in samples)
print(f"\nFace samples: {len(samples)} ({found} with a face, {len(samples) - found} unavailable)")

if len(times) > 1:
    gaps = [b - a for a, b in zip(times, times[1:])]
    print(f"  rate: {(len(times) - 1) / (times[-1] - times[0]):.1f}/sec, largest gap: {max(gaps):.2f}s")
    if end is not None:
        print("  all samples inside the hand window:", all(start <= t <= end for t in times))