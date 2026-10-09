import os
from cards import new_deck, draw, show_cards, evaluate
from ai import choose_action, choose_raise

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
        
        if who == "player":
            show_table()
            action = get_action(to_call, max_raise)
            label = "You"
        else:
            action = choose_action(to_call, max_raise)
            label = "AI"
            
        if action == "fold":
            say(f"{label} folded!")
            return who
        
        elif action == "check":
            say(f"{label} checked.")
            if not first:
                break
        
        elif action == "call":
            pay(who, to_call)
            say(f"{label}: call {to_call}")
            return None
        
        elif action == "raise":
            if who == "player":
                raise_amount = get_raise(max_raise)
            else:
                raise_amount = choose_raise(max_raise)
                
            pay(who, to_call + raise_amount)
            to_call += raise_amount
            say(f"{label}: raise {raise_amount} (total to call: {to_call})")
            
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
    
    ante = min(ANTE, table["player"], table["ai"])
    pay("player", ante)
    pay("ai", ante)
    
    for name, count in [("Preflop", 0), ("Flop", 3), ("Turn", 1), ("River", 1)]:
        table["board"] += draw(deck, count)
        say(f"--- {name} ---")

        #Skip betting if someone is all in
        if min(table["player"], table["ai"]) == 0:
            show_table()
            input("Someone is all in. Press Enter to continue...")
            continue

        folder = betting_round()
        if folder:
            winner = "ai" if folder == "player" else "player"
            give_pot(winner)
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
        give_pot("player")
    elif player_score > ai_score:
        give_pot("ai")
    else:
        say("Tie! Pot is split")
        half = table["pot"] // 2
        table["player"] += half
        table["ai"] += table["pot"] - half
        table["pot"] = 0

    show_table()