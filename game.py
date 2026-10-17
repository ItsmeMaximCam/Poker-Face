import os
import time
from cards import new_deck, draw, show_cards, evaluate
from ai import choose_action, choose_raise
from recorder import start_hand, new_street, record_event, end_hand

STARTING_CHIPS = 100
ANTE = 5

table = {"player": STARTING_CHIPS, "ai": STARTING_CHIPS, "pot": 0,
         "cards": [], "board": [], "log": []}
names = {"player": "You", "ai": "the AI"}

def clear():
    os.system("cls" if os.name == "nt" else "clear")
    
def say(text):
    table["log"].append(text)

def pay(who, amount):
    table[who] -= amount
    table["pot"] += amount
    
def show_table():
    clear()
    for line in table["log"]:
        print(line)
    print()
    if table["board"]:
        print("Board:", show_cards(table["board"]))
    print("Your cards:", show_cards(table["cards"]))
    if len(table["board"]) >= 3:
        _, best_hand = evaluate(table["cards"], table["board"])
        print("Your best hand:", best_hand)
    else:
        print("Your best hand: not determined until the flop")
    print(f"Pot: {table['pot']} | Your Chips: {table['player']} | AI Chips: {table['ai']}")
    print()


def get_action(to_call, max_raise):
    if to_call == 0:
        options = ["check", "raise", "fold"]
    else:
        options = ["call", "raise", "fold"]
    if max_raise < 1:
        options.remove("raise")
        
    while True:
        action = input(" / ".join(options) + ": ").lower().strip()
        
        if action in options:
            return action
        
        print("Invalid")

def get_raise(max_raise):
    while True:
        text = input(f"Raise by how much? (1-{max_raise}): ").strip()
        if text.isdigit() and 1 <= int(text) <= max_raise:
            return int(text)
        print("Invalid")

def betting_round():
    """Returning who folded or none if the round finished normally"""
    to_call = 0
    who = "player"
    first = True
    
    while True:
        other = "ai" if who == "player" else "player"
        max_raise = max(0, min(table[who] - to_call, table[other]))
        
        decision_time = None
        acted_at = None
        
        if who == "player":
            show_table()
            start = time.time()
            action = get_action(to_call, max_raise)
            acted_at = time.time()
            decision_time = acted_at - start
            label = "You"
        else:
            action = choose_action(to_call, max_raise)
            label = "AI"
            
        if action == "fold":
            say(f"{label} folded!")
            record_event(f"{who}_action", "fold" , 0, decision_time, acted_at)
            return who
        
        elif action == "check":
            say(f"{label} checked.")
            record_event(f"{who}_action", "check", 0, decision_time, acted_at)
            if not first:
                break
        
        elif action == "call":
            pay(who, to_call)
            say(f"{label}: call {to_call}")
            record_event(f"{who}_action", "call", to_call, decision_time, acted_at)
            return None
        
        elif action == "raise":
            if who == "player":
                raise_amount = get_raise(max_raise)
            else:
                raise_amount = choose_raise(max_raise)
                
            pay(who, to_call + raise_amount)
            to_call += raise_amount
            say(f"{label}: raise {raise_amount} (total to call: {to_call})")
            record_event(f"{who}_action", "raise", raise_amount, decision_time, acted_at)
        first = False
        who = other
        
def give_pot(who):
    say(f"The pot of {table['pot']} goes to {names[who]}.")
    table[who] += table["pot"]
    table["pot"] = 0
    

def play_hand():
    deck = new_deck()
    
    table["cards"] = draw(deck, 2)
    ai_cards = draw(deck, 2)
    table["board"] = []
    table["log"] = []
    
    start_hand()
    
    ante = min(ANTE, table["player"], table["ai"])
    pay("player", ante)
    pay("ai", ante)
    
    for name, count in [("Preflop", 0), ("Flop", 3), ("Turn", 1), ("River", 1)]:
        table["board"] += draw(deck, count)
        say(f"--- {name} ---")
        if count > 0:
            new_street(name)

        #Skip betting if someone is all in
        if min(table["player"], table["ai"]) == 0:
            show_table()
            input("Someone is all in. Press Enter to continue...")
            continue

        folder = betting_round()
        if folder:
            winner = "ai" if folder == "player" else "player"
            give_pot(winner)
            end_hand(table["cards"], ai_cards, table["board"], winner, "fold")
            show_table()
            return


    #showdown
    player_score, player_hand = evaluate(table["cards"], table["board"])
    ai_score, ai_hand = evaluate(ai_cards, table["board"])

    say("--- Showdown ---")
    say("AI cards: " + show_cards(ai_cards))
    say(f"Your hand: {player_hand}")
    say(f"AI hand: {ai_hand}")

    if player_score < ai_score:
        winner = "player"
        give_pot("player")
    elif player_score > ai_score:
        winner = "ai"
        give_pot("ai")
    else:
        winner = ("tie")
        say("Tie! Pot is split")
        half = table["pot"] // 2
        table["player"] += half
        table["ai"] += table["pot"] - half
        table["pot"] = 0
        
    end_hand(table["cards"], ai_cards, table["board"], winner, "showdown")
    show_table()