from treys import Card, Deck, Evaluator

evaluator = Evaluator()

#Trey rank classes
RANK_NAMES = {
    1: "Straight Flush",
    2: "Four of a Kind",
    3: "Full House",
    4: "Flush",
    5: "Straight",
    6: "Three of a Kind",
    7: "Two Pair",
    8: "One Pair",
    9: "High Card"
}

def new_deck():
    return Deck()

def draw(deck, amount):
    cards = deck.draw(amount)
    return cards if isinstance(cards, list) else [cards]

def card_name(card):
    return Card.int_to_pretty_str(card)

def show_cards(cards):
    return " ".join(card_name(card) for card in cards)

def evaluate(hole, board):
    score = evaluator.evaluate(board, hole)
    rank = evaluator.get_rank_class(score)
    return score, RANK_NAMES[rank]