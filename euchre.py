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


# --- Bidding AI heuristic --------------------------------------------------
# Thresholds are deliberately simple and tunable -- adjust these to make the
# AI more or less aggressive about bidding.
ORDER_UP_THRESHOLD = 45
ALONE_THRESHOLD = 80


def hand_trump_strength(hand, trump):
    trump_cards = [c for c in hand if effective_suit(c, trump) == trump]
    return len(trump_cards) * 10 + sum(card_strength(c, trump) for c in trump_cards)


def recommend_bid_action(hand, round_num, is_dealer, turned_suit=None, available_suits=None):
    if round_num == 1:
        strength = hand_trump_strength(hand, turned_suit)
        if strength >= ALONE_THRESHOLD:
            return "order_up_alone"
        if strength >= ORDER_UP_THRESHOLD:
            return "order_up"
        return "pass"

    best_suit, best_strength = None, -1
    for suit in available_suits:
        strength = hand_trump_strength(hand, suit)
        if strength > best_strength:
            best_suit, best_strength = suit, strength
    if best_strength >= ALONE_THRESHOLD:
        return (best_suit, True)
    # is_dealer means "stuck the dealer": round 2 forces a call, so a weak
    # hand still calls the best available suit rather than passing.
    if best_strength >= ORDER_UP_THRESHOLD or is_dealer:
        return (best_suit, False)
    return "pass"


def recommend_discard(hand, trump):
    return min(hand, key=lambda c: card_strength(c, trump))
