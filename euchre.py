"""Terminal Euchre game with simple AI opponents and a persistent MMR system."""

import random
import json

# --- Constants -------------------------------------------------------------

SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"]
RANKS = ["9", "10", "J", "Q", "K", "A"]
RANK_ORDER = {"9": 0, "10": 1, "J": 2, "Q": 3, "K": 4, "A": 5}
SAME_COLOR = {"Spades": "Clubs", "Clubs": "Spades", "Hearts": "Diamonds", "Diamonds": "Hearts"}

RULES = {
    "allow_going_alone": True,
    "stick_the_dealer": False,
    "farmers_hand": False,
}


# --- Deck --------------------------------------------------------------

def create_deck():
    return [(rank, suit) for suit in SUITS for rank in RANKS]
