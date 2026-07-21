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


# --- Trump / bower ranking ---------------------------------------------

def effective_suit(card, trump):
    rank, suit = card
    if rank == "J" and SAME_COLOR[suit] == trump:
        return trump
    return suit


def card_strength(card, trump):
    rank, suit = card
    if rank == "J" and suit == trump:
        return 31  # right bower: highest card in the game
    if rank == "J" and SAME_COLOR[suit] == trump:
        return 30  # left bower: second-highest, printed suit doesn't matter
    if effective_suit(card, trump) == trump:
        return 20 + RANK_ORDER[rank]
    return RANK_ORDER[rank]


# --- Dealing -------------------------------------------------------------

def deal_hands(deck):
    hands = [deck[i * 5:(i + 1) * 5] for i in range(4)]
    up_card = deck[20]
    hidden_kitty = deck[21:24]
    return hands, up_card, hidden_kitty


# --- Dealer pick-up, discard, and farmer's hand swap ---------------------

def pick_up_card(dealer_hand, up_card):
    return dealer_hand + [up_card]


def discard(hand, card_to_discard):
    new_hand = hand[:]
    new_hand.remove(card_to_discard)
    return new_hand


def is_farmers_hand(hand):
    return len(hand) == 5 and all(rank in ("9", "10") for rank, _ in hand)


def swap_farmers_hand(hand, keep_cards, hidden_kitty):
    return keep_cards + hidden_kitty
