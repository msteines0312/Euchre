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


# --- Bidding orchestration --------------------------------------------------

def run_round1_bidding(hands, turned_suit, dealer_seat, decision_fns):
    for offset in range(1, 5):
        seat = (dealer_seat + offset) % 4
        action = decision_fns[seat](hands[seat], turned_suit)
        if action == "order_up":
            return seat, False
        if action == "order_up_alone":
            return seat, True
    return None


def run_round2_bidding(hands, turned_suit, dealer_seat, decision_fns, stick_the_dealer):
    available_suits = [suit for suit in SUITS if suit != turned_suit]
    for offset in range(1, 5):
        seat = (dealer_seat + offset) % 4
        is_dealer_seat = seat == dealer_seat
        must_call = stick_the_dealer and is_dealer_seat
        action = decision_fns[seat](hands[seat], available_suits, must_call)
        if action != "pass":
            suit, alone = action
            return seat, suit, alone
    return None


# --- Card-play legality and AI heuristic ------------------------------------

def legal_plays(hand, led_suit, trump):
    if led_suit is None:
        return hand[:]
    following = [c for c in hand if effective_suit(c, trump) == led_suit]
    return following if following else hand[:]


def is_legal_play(card, hand, led_suit, trump):
    return card in legal_plays(hand, led_suit, trump)


def recommend_card_play(hand, trick_so_far, trump, led_suit):
    options = legal_plays(hand, led_suit, trump)
    if led_suit is None:
        return max(options, key=lambda c: card_strength(c, trump))

    if trick_so_far:
        best_played_strength = max(card_strength(c, trump) for c in trick_so_far)
        winning_options = [c for c in options if card_strength(c, trump) > best_played_strength]
    else:
        winning_options = options

    if winning_options:
        return min(winning_options, key=lambda c: card_strength(c, trump))
    return min(options, key=lambda c: card_strength(c, trump))


# --- Trick orchestration -----------------------------------------------

def determine_trick_winner(plays, trump):
    led_suit = effective_suit(plays[0][1], trump)

    def rank(play):
        seat, card = play
        if effective_suit(card, trump) == trump:
            return (2, card_strength(card, trump))
        if card[1] == led_suit:
            return (1, card_strength(card, trump))
        return (0, 0)

    winner_seat, _ = max(plays, key=rank)
    return winner_seat


def play_trick(hands, leader_seat, trump, sitting_out_seat, decision_fns):
    plays = []
    led_suit = None
    seat = leader_seat
    for _ in range(4):
        if seat == sitting_out_seat:
            seat = (seat + 1) % 4
            continue
        hand = hands[seat]
        card = decision_fns[seat](hand, [c for _, c in plays], trump, led_suit)
        hand.remove(card)
        if led_suit is None:
            led_suit = effective_suit(card, trump)
        plays.append((seat, card))
        seat = (seat + 1) % 4
    winner_seat = determine_trick_winner(plays, trump)
    return winner_seat, plays


# --- Scoring -------------------------------------------------------------

def score_hand(tricks_by_team, making_team, went_alone):
    other_team = 1 - making_team
    made_tricks = tricks_by_team[making_team]

    if made_tricks < 3:
        return {making_team: 0, other_team: 2}
    if made_tricks == 5:
        return {making_team: 4 if went_alone else 2, other_team: 0}
    return {making_team: 1, other_team: 0}


# --- MMR / difficulty --------------------------------------------------
# K and BASELINE are tunable: BASELINE is the "expected at any rating"
# decision-quality rate, K controls how fast MMR moves per hand.
K = 20
BASELINE = 0.6
DEFAULT_MMR = {"mmr": 1000, "games_played": 0}


def load_mmr(path="mmr.json"):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return dict(DEFAULT_MMR)


def save_mmr(data, path="mmr.json"):
    with open(path, "w") as f:
        json.dump(data, f)


def compute_quality_rate(decisions_log):
    if not decisions_log:
        return 1.0
    matches = sum(1 for actual, recommended in decisions_log if actual == recommended)
    return matches / len(decisions_log)


def update_mmr(mmr, quality_rate):
    return mmr + round(K * (quality_rate - BASELINE))


def difficulty_tier(mmr):
    if mmr < 900:
        return "easy"
    if mmr < 1500:
        return "medium"
    return "hard"
