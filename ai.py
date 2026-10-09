import random

def choose_action(calling, can_raise):
    if calling == 0:
        options = {"check": 70, "raise": 30}
    else: 
        options = {"fold": 20, "call": 60, "raise": 20}
    
    if not can_raise:
        options.pop("raise", None)
        
    return random.choices(list(options), weights=list(options.values()))[0]

def choose_raise(max_raise):
    return min(max_raise, random.choice([10, 20, 30, 40, 50]))