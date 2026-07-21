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


# --- Difficulty mistake-rate wrapper -----------------------------------

MISTAKE_RATES = {"easy": 0.30, "medium": 0.15, "hard": 0.0}


def apply_mistake(recommended, alternatives, mistake_rate, rng=random):
    if alternatives and rng.random() < mistake_rate:
        return rng.choice(alternatives)
    return recommended


def make_ai_bid_decision_fn(mistake_rate, rng=random):
    def decision_fn(hand, turned_suit_or_available, must_call=False):
        if isinstance(turned_suit_or_available, list):
            recommended = recommend_bid_action(
                hand, round_num=2, is_dealer=must_call, available_suits=turned_suit_or_available
            )
            alternatives = ["pass"] if recommended != "pass" and not must_call else []
        else:
            recommended = recommend_bid_action(hand, round_num=1, is_dealer=False, turned_suit=turned_suit_or_available)
            alternatives = ["pass"] if recommended != "pass" else []
        return apply_mistake(recommended, alternatives, mistake_rate, rng)
    return decision_fn


def make_ai_card_decision_fn(mistake_rate, rng=random):
    def decision_fn(hand, trick_so_far, trump, led_suit):
        recommended = recommend_card_play(hand, trick_so_far, trump, led_suit)
        options = legal_plays(hand, led_suit, trump)
        alternatives = [c for c in options if c != recommended]
        return apply_mistake(recommended, alternatives, mistake_rate, rng)
    return decision_fn


def make_ai_discard_decision_fn(mistake_rate, rng=random):
    def decision_fn(hand, trump):
        recommended = recommend_discard(hand, trump)
        alternatives = [c for c in hand if c != recommended]
        return apply_mistake(recommended, alternatives, mistake_rate, rng)
    return decision_fn


# --- Human decision functions (terminal I/O + oracle logging) ---------------

def _prompt_choice(prompt, valid_choices):
    while True:
        raw = input(prompt).strip()
        if raw in valid_choices:
            return raw
        print(f"Please enter one of: {', '.join(valid_choices)}")


def make_human_bid_decision_fn(decisions_log):
    def decision_fn(hand, turned_suit_or_available, must_call=False):
        print(f"Your hand: {hand}")
        if isinstance(turned_suit_or_available, list):
            recommended = recommend_bid_action(
                hand, round_num=2, is_dealer=must_call, available_suits=turned_suit_or_available
            )
            choices = turned_suit_or_available + (["pass"] if not must_call else [])
            raw = _prompt_choice(f"Call a suit ({', '.join(choices)}) or pass: ", choices)
            actual = "pass" if raw == "pass" else (raw, False)  # False = not going alone (round 2 alone calls aren't offered here yet)
        else:
            recommended = recommend_bid_action(hand, round_num=1, is_dealer=False, turned_suit=turned_suit_or_available)
            raw = _prompt_choice("Order it up, go alone, or pass? (order_up/order_up_alone/pass): ",
                                  ["order_up", "order_up_alone", "pass"])
            actual = raw
        decisions_log.append((actual, recommended))
        return actual
    return decision_fn


def make_human_card_decision_fn(decisions_log):
    def decision_fn(hand, trick_so_far, trump, led_suit):
        recommended = recommend_card_play(hand, trick_so_far, trump, led_suit)
        options = legal_plays(hand, led_suit, trump)
        print(f"Your hand: {hand}")
        print(f"Legal plays: {options}")
        while True:
            raw = input("Play a card (rank suit): ").strip().split()
            if len(raw) == 2 and tuple(raw) in options:
                actual = (raw[0], raw[1])
                break
            print(f"Please enter one of: {options}")
        decisions_log.append((actual, recommended))
        return actual
    return decision_fn


def make_human_discard_decision_fn(decisions_log):
    def decision_fn(hand, trump):
        recommended = recommend_discard(hand, trump)
        print(f"Your hand after picking up the up-card: {hand}")
        while True:
            raw = input("Discard a card (rank suit): ").strip().split()
            if len(raw) == 2 and tuple(raw) in hand:
                actual = (raw[0], raw[1])
                break
            print(f"Please enter one of: {hand}")
        decisions_log.append((actual, recommended))
        return actual
    return decision_fn


# --- Full hand and game loop -----------------------------------------------

TEAM_OF_SEAT = {0: 0, 2: 0, 1: 1, 3: 1}


def play_hand(hands, dealer_seat, up_card, hidden_kitty, bid_decision_fns, card_decision_fns, discard_decision_fns):
    turned_suit = up_card[1]

    result = run_round1_bidding(hands, turned_suit, dealer_seat, bid_decision_fns)
    trump = turned_suit
    if result is not None:
        maker_seat, alone = result
        hands[dealer_seat] = pick_up_card(hands[dealer_seat], up_card)
        discard_choice = discard_decision_fns[dealer_seat](hands[dealer_seat], trump)
        hands[dealer_seat] = discard(hands[dealer_seat], discard_choice)
    else:
        # bid_decision_fns entries already accept (hand, available_suits, must_call) for
        # round 2 -- see make_ai_bid_decision_fn / make_human_bid_decision_fn (Tasks 11/12).
        result = run_round2_bidding(hands, turned_suit, dealer_seat, bid_decision_fns, RULES["stick_the_dealer"])
        if result is None:
            return None
        maker_seat, trump, alone = result

    making_team = TEAM_OF_SEAT[maker_seat]
    sitting_out_seat = (maker_seat + 2) % 4 if alone else None

    tricks_by_team = {0: 0, 1: 0}
    leader_seat = (dealer_seat + 1) % 4
    if leader_seat == sitting_out_seat:
        leader_seat = (leader_seat + 1) % 4

    for _ in range(5):
        winner_seat, plays = play_trick(hands, leader_seat, trump, sitting_out_seat, card_decision_fns)
        tricks_by_team[TEAM_OF_SEAT[winner_seat]] += 1
        leader_seat = winner_seat

    points_by_team = score_hand(tricks_by_team, making_team, alone)
    return points_by_team, making_team, alone


def play_game(bid_decision_fns, card_decision_fns, discard_decision_fns):
    scores = {0: 0, 1: 0}
    dealer_seat = 0
    while max(scores.values()) < 10:
        deck = create_deck()
        random.shuffle(deck)
        hands, up_card, hidden_kitty = deal_hands(deck)
        result = play_hand(hands, dealer_seat, up_card, hidden_kitty,
                            bid_decision_fns, card_decision_fns, discard_decision_fns)
        if result is not None:
            points_by_team, _, _ = result
            for team, points in points_by_team.items():
                scores[team] += points
        dealer_seat = (dealer_seat + 1) % 4
    return 0 if scores[0] > scores[1] else 1


def main():
    mmr_data = load_mmr()
    tier = difficulty_tier(mmr_data["mmr"])
    print(f"Current MMR: {mmr_data['mmr']} ({tier} difficulty)")
    override = input("Press Enter to play at this difficulty, or type easy/medium/hard to override: ").strip()
    if override in MISTAKE_RATES:
        tier = override

    decisions_log = []
    bid_decision_fns = [
        make_human_bid_decision_fn(decisions_log),
        make_ai_bid_decision_fn(MISTAKE_RATES[tier]),
        make_ai_bid_decision_fn(MISTAKE_RATES[tier]),
        make_ai_bid_decision_fn(MISTAKE_RATES[tier]),
    ]
    card_decision_fns = [
        make_human_card_decision_fn(decisions_log),
        make_ai_card_decision_fn(MISTAKE_RATES[tier]),
        make_ai_card_decision_fn(MISTAKE_RATES[tier]),
        make_ai_card_decision_fn(MISTAKE_RATES[tier]),
    ]
    discard_decision_fns = [
        make_human_discard_decision_fn(decisions_log),
        make_ai_discard_decision_fn(MISTAKE_RATES[tier]),
        make_ai_discard_decision_fn(MISTAKE_RATES[tier]),
        make_ai_discard_decision_fn(MISTAKE_RATES[tier]),
    ]

    winning_team = play_game(bid_decision_fns, card_decision_fns, discard_decision_fns)
    print(f"Team {winning_team} wins the game!")

    quality_rate = compute_quality_rate(decisions_log)
    mmr_data["mmr"] = update_mmr(mmr_data["mmr"], quality_rate)
    mmr_data["games_played"] += 1
    save_mmr(mmr_data)
    print(f"Your decisions matched sound play {quality_rate:.0%} of the time. "
          f"New MMR: {mmr_data['mmr']}")


if __name__ == "__main__":
    main()
