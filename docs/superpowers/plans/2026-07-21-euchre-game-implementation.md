# Euchre Terminal Game Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable terminal Euchre game (`euchre.py`) with simple AI opponents, configurable house-rule variants, and a persistent MMR/difficulty system, matching `docs/superpowers/specs/2026-07-21-euchre-game-design.md`.

**Architecture:** Single file `euchre.py`, built bottom-up: pure card/rule logic first (fully unit-testable, no I/O), then orchestration functions that take injectable `decision_fn` callables (so bidding/trick-play control flow is testable without mocking `input()`), then a thin `main()` that wires human terminal I/O and AI heuristics into those orchestration functions.

**Tech Stack:** Python 3, `pytest` for tests, standard library only (`random`, `json`, no third-party dependencies).

## Global Constraints

- Single file `euchre.py`, organized top-to-bottom in the section order: constants/deck, trump ranking, dealing, bidding mechanics, AI heuristics, bidding orchestration, card-play mechanics, trick orchestration, scoring, MMR, difficulty, human I/O, main game loop.
- Cards are plain `(rank, suit)` tuples — no `Card` class.
- All tests in `tests/test_euchre.py`, added alongside each task (not batched at the end).
- No comments explaining *what* code does — only *why*, where a design decision is non-obvious (e.g., threshold constants, the farmer's-hand card-count resolution).
- `RULES` dict constants (`allow_going_alone`, `stick_the_dealer`, `farmers_hand`) and MMR/difficulty constants (`K`, `BASELINE`, tier thresholds, `MISTAKE_RATES`) must all be defined near the top of the file so they're easy to find and tweak.

---

### Task 1: Constants and deck creation

**Files:**
- Create: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Produces: `SUITS: list[str]`, `RANKS: list[str]`, `RANK_ORDER: dict[str,int]`, `SAME_COLOR: dict[str,str]`, `create_deck() -> list[tuple[str,str]]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_euchre.py
from euchre import create_deck, SUITS, RANKS

def test_create_deck_has_24_unique_cards():
    deck = create_deck()
    assert len(deck) == 24
    assert len(set(deck)) == 24

def test_create_deck_has_all_suits_and_ranks():
    deck = create_deck()
    for suit in SUITS:
        for rank in RANKS:
            assert (rank, suit) in deck
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'euchre'`

- [ ] **Step 3: Write minimal implementation**

```python
# euchre.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git init
git add euchre.py tests/test_euchre.py docs/superpowers
git commit -m "Add deck creation and core constants"
```

---

### Task 2: Trump and bower ranking

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `SAME_COLOR`, `RANK_ORDER` (Task 1)
- Produces: `effective_suit(card, trump) -> str`, `card_strength(card, trump) -> int`

- [ ] **Step 1: Write the failing tests**

```python
from euchre import effective_suit, card_strength

def test_left_bower_effective_suit_is_trump():
    assert effective_suit(("J", "Clubs"), "Spades") == "Spades"

def test_non_bower_effective_suit_is_own_suit():
    assert effective_suit(("A", "Hearts"), "Spades") == "Hearts"

def test_bower_ranking_order():
    trump = "Spades"
    right_bower = ("J", "Spades")
    left_bower = ("J", "Clubs")
    trump_ace = ("A", "Spades")
    offsuit_ace = ("A", "Hearts")
    assert card_strength(right_bower, trump) > card_strength(left_bower, trump)
    assert card_strength(left_bower, trump) > card_strength(trump_ace, trump)
    assert card_strength(trump_ace, trump) > card_strength(offsuit_ace, trump)

def test_offsuit_cards_rank_by_face_value_only():
    trump = "Spades"
    assert card_strength(("A", "Hearts"), trump) > card_strength(("9", "Hearts"), trump)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'effective_suit'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add trump and bower ranking logic"
```

---

### Task 3: Dealing

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `create_deck()` (Task 1)
- Produces: `deal_hands(deck) -> tuple[list[list[tuple]], tuple, list[tuple]]` — returns `(hands, up_card, hidden_kitty)`. `deck` must already be in dealing order (shuffled by the caller); this function only slices it.

- [ ] **Step 1: Write the failing test**

```python
from euchre import deal_hands, create_deck

def test_deal_hands_gives_four_five_card_hands():
    deck = create_deck()
    hands, up_card, hidden_kitty = deal_hands(deck)
    assert len(hands) == 4
    assert all(len(hand) == 5 for hand in hands)

def test_deal_hands_up_card_and_kitty_use_remaining_cards():
    deck = create_deck()
    hands, up_card, hidden_kitty = deal_hands(deck)
    assert len(hidden_kitty) == 3
    dealt = [card for hand in hands for card in hand] + [up_card] + hidden_kitty
    assert sorted(dealt) == sorted(deck)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'deal_hands'`

- [ ] **Step 3: Write minimal implementation**

```python
# --- Dealing -------------------------------------------------------------

def deal_hands(deck):
    hands = [deck[i * 5:(i + 1) * 5] for i in range(4)]
    up_card = deck[20]
    hidden_kitty = deck[21:24]
    return hands, up_card, hidden_kitty
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add dealing logic"
```

---

### Task 4: Dealer pick-up/discard and farmer's hand swap

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Produces: `pick_up_card(dealer_hand, up_card) -> list[tuple]`, `discard(hand, card_to_discard) -> list[tuple]`, `is_farmers_hand(hand) -> bool`, `swap_farmers_hand(hand, keep_cards, hidden_kitty) -> list[tuple]`

- [ ] **Step 1: Write the failing tests**

```python
from euchre import pick_up_card, discard, is_farmers_hand, swap_farmers_hand

def test_pick_up_card_adds_up_card_to_hand():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("J", "Hearts"), ("Q", "Hearts"), ("K", "Hearts")]
    picked_up = pick_up_card(hand, ("A", "Hearts"))
    assert len(picked_up) == 6
    assert ("A", "Hearts") in picked_up

def test_discard_removes_exactly_one_card():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("J", "Hearts"), ("Q", "Hearts"), ("K", "Hearts"), ("A", "Hearts")]
    result = discard(hand, ("9", "Hearts"))
    assert len(result) == 5
    assert ("9", "Hearts") not in result

def test_is_farmers_hand_true_for_all_nines_and_tens():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("9", "Spades"), ("10", "Spades"), ("9", "Clubs")]
    assert is_farmers_hand(hand) is True

def test_is_farmers_hand_false_with_a_face_card():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("9", "Spades"), ("10", "Spades"), ("J", "Clubs")]
    assert is_farmers_hand(hand) is False

def test_swap_farmers_hand_combines_kept_cards_and_kitty():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("9", "Spades"), ("10", "Spades"), ("9", "Clubs")]
    keep_cards = [("9", "Hearts"), ("10", "Hearts")]
    hidden_kitty = [("A", "Clubs"), ("K", "Diamonds"), ("Q", "Spades")]
    new_hand = swap_farmers_hand(hand, keep_cards, hidden_kitty)
    assert len(new_hand) == 5
    assert sorted(new_hand) == sorted(keep_cards + hidden_kitty)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'pick_up_card'`

- [ ] **Step 3: Write minimal implementation**

```python
# --- Dealer pick-up, discard, and farmer's hand swap ---------------------

def pick_up_card(dealer_hand, up_card):
    return dealer_hand + [up_card]


def discard(hand, card_to_discard):
    new_hand = hand[:]
    new_hand.remove(card_to_discard)
    return new_hand


def is_farmers_hand(hand):
    return all(rank in ("9", "10") for rank, _ in hand)


def swap_farmers_hand(hand, keep_cards, hidden_kitty):
    return keep_cards + hidden_kitty
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add dealer pick-up/discard and farmer's hand swap mechanics"
```

---

### Task 5: Bidding AI heuristic

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `effective_suit`, `card_strength` (Task 2)
- Produces: `hand_trump_strength(hand, trump) -> int`, `recommend_bid_action(hand, round_num, is_dealer, turned_suit=None, available_suits=None) -> str | tuple`, `recommend_discard(hand, trump) -> tuple`
  - Round 1 (`turned_suit` given): returns `"pass"`, `"order_up"`, or `"order_up_alone"`.
  - Round 2 (`available_suits` given): returns `"pass"`, or `(suit, alone: bool)` for the best suit to call.
  - `recommend_discard` is a separate function from `recommend_card_play` (Task 7) on purpose: discarding wants the *weakest* card in a hand, the opposite of what you'd want to lead or play.

- [ ] **Step 1: Write the failing tests**

```python
from euchre import recommend_bid_action

def test_recommend_pass_on_weak_hand_round_1():
    weak_hand = [("9", "Hearts"), ("10", "Diamonds"), ("Q", "Clubs"), ("9", "Diamonds"), ("K", "Hearts")]
    assert recommend_bid_action(weak_hand, round_num=1, is_dealer=False, turned_suit="Spades") == "pass"

def test_recommend_order_up_on_strong_hand_round_1():
    strong_hand = [("J", "Spades"), ("J", "Clubs"), ("A", "Spades"), ("K", "Spades"), ("9", "Hearts")]
    assert recommend_bid_action(strong_hand, round_num=1, is_dealer=False, turned_suit="Spades") == "order_up_alone"

def test_recommend_pass_round_2_on_weak_hand():
    weak_hand = [("9", "Hearts"), ("10", "Diamonds"), ("Q", "Clubs"), ("9", "Diamonds"), ("K", "Hearts")]
    result = recommend_bid_action(weak_hand, round_num=2, is_dealer=False, available_suits=["Hearts", "Diamonds", "Clubs"])
    assert result == "pass"

def test_recommend_call_best_suit_round_2():
    hand = [("J", "Diamonds"), ("J", "Hearts"), ("A", "Diamonds"), ("K", "Diamonds"), ("9", "Clubs")]
    result = recommend_bid_action(hand, round_num=2, is_dealer=False, available_suits=["Hearts", "Diamonds", "Clubs"])
    assert result[0] == "Diamonds"

def test_recommend_discard_picks_weakest_card():
    from euchre import recommend_discard
    hand = [("9", "Hearts"), ("A", "Spades"), ("J", "Spades"), ("Q", "Diamonds"), ("K", "Clubs"), ("10", "Hearts")]
    # trump is Spades: A/J-Spades are strong trump, the rest are weak off-suit cards.
    # 9-Hearts is the single weakest card by card_strength.
    assert recommend_discard(hand, trump="Spades") == ("9", "Hearts")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'recommend_bid_action'`

- [ ] **Step 3: Write minimal implementation**

```python
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
    if best_strength >= ORDER_UP_THRESHOLD:
        return (best_suit, False)
    return "pass"


def recommend_discard(hand, trump):
    return min(hand, key=lambda c: card_strength(c, trump))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (18 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add bidding AI heuristic"
```

---

### Task 6: Bidding orchestration

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: nothing new (works with plain `decision_fn` callables supplied by the caller — real AI/human wiring comes in later tasks)
- Produces:
  - `run_round1_bidding(hands, turned_suit, dealer_seat, decision_fns) -> tuple[int, bool] | None` — `decision_fns[seat](hand, turned_suit) -> "pass"|"order_up"|"order_up_alone"`. Returns `(maker_seat, alone)` or `None` if all four pass.
  - `run_round2_bidding(hands, turned_suit, dealer_seat, decision_fns, stick_the_dealer) -> tuple[int, str, bool] | None` — `decision_fns[seat](hand, available_suits, must_call) -> "pass"|(suit, alone)`. Returns `(maker_seat, suit, alone)` or `None` if redeal is needed.

- [ ] **Step 1: Write the failing tests**

```python
from euchre import run_round1_bidding, run_round2_bidding

def test_round1_bidding_returns_first_non_pass():
    hands = [[], [], [], []]
    decisions = ["pass", "order_up", "pass", "pass"]
    decision_fns = [lambda h, s, d=d: d for d in decisions]
    result = run_round1_bidding(hands, "Spades", dealer_seat=0, decision_fns=decision_fns)
    assert result == (1, False)

def test_round1_bidding_returns_none_if_all_pass():
    hands = [[], [], [], []]
    decision_fns = [lambda h, s: "pass" for _ in range(4)]
    result = run_round1_bidding(hands, "Spades", dealer_seat=0, decision_fns=decision_fns)
    assert result is None

def test_round1_bidding_starts_left_of_dealer():
    hands = [[], [], [], []]
    order_seen = []
    def make_fn(seat):
        def fn(hand, turned_suit):
            order_seen.append(seat)
            return "pass"
        return fn
    decision_fns = [make_fn(seat) for seat in range(4)]
    run_round1_bidding(hands, "Spades", dealer_seat=1, decision_fns=decision_fns)
    assert order_seen == [2, 3, 0, 1]

def test_round2_bidding_returns_maker_suit_and_alone():
    hands = [[], [], [], []]
    decisions = ["pass", ("Hearts", True), "pass", "pass"]
    decision_fns = [lambda h, s, m, d=d: d for d in decisions]
    result = run_round2_bidding(hands, "Spades", dealer_seat=0, decision_fns=decision_fns, stick_the_dealer=False)
    assert result == (1, "Hearts", True)

def test_round2_bidding_returns_none_when_all_pass_and_no_stick_the_dealer():
    hands = [[], [], [], []]
    decision_fns = [lambda h, s, m: "pass" for _ in range(4)]
    result = run_round2_bidding(hands, "Spades", dealer_seat=0, decision_fns=decision_fns, stick_the_dealer=False)
    assert result is None

def test_round2_bidding_forces_dealer_call_when_stick_the_dealer():
    hands = [[], [], [], []]
    def dealer_fn(hand, available_suits, must_call):
        assert must_call is True
        return ("Hearts", False)
    decision_fns = [lambda h, s, m: "pass", lambda h, s, m: "pass", lambda h, s, m: "pass", dealer_fn]
    result = run_round2_bidding(hands, "Spades", dealer_seat=3, decision_fns=decision_fns, stick_the_dealer=True)
    assert result == (3, "Hearts", False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'run_round1_bidding'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (24 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add bidding orchestration with injectable decision functions"
```

---

### Task 7: Legal plays and card-play AI heuristic

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `effective_suit`, `card_strength` (Task 2)
- Produces: `legal_plays(hand, led_suit, trump) -> list[tuple]`, `is_legal_play(card, hand, led_suit, trump) -> bool`, `recommend_card_play(hand, trick_so_far, trump, led_suit) -> tuple`

- [ ] **Step 1: Write the failing tests**

```python
from euchre import legal_plays, is_legal_play, recommend_card_play

def test_legal_plays_when_leading_is_full_hand():
    hand = [("9", "Hearts"), ("A", "Spades")]
    assert legal_plays(hand, led_suit=None, trump="Clubs") == hand

def test_legal_plays_must_follow_suit_if_possible():
    hand = [("9", "Hearts"), ("A", "Spades"), ("K", "Hearts")]
    result = legal_plays(hand, led_suit="Hearts", trump="Clubs")
    assert result == [("9", "Hearts"), ("K", "Hearts")]

def test_legal_plays_left_bower_counts_as_trump_for_following():
    hand = [("J", "Hearts"), ("9", "Spades")]  # trump is Diamonds, Hearts is same color
    result = legal_plays(hand, led_suit="Diamonds", trump="Diamonds")
    assert result == [("J", "Hearts")]

def test_legal_plays_any_card_if_cannot_follow_suit():
    hand = [("9", "Spades"), ("K", "Clubs")]
    result = legal_plays(hand, led_suit="Hearts", trump="Diamonds")
    assert result == hand

def test_is_legal_play_true_and_false():
    hand = [("9", "Hearts"), ("A", "Spades")]
    assert is_legal_play(("9", "Hearts"), hand, led_suit="Hearts", trump="Clubs") is True
    assert is_legal_play(("A", "Spades"), hand, led_suit="Hearts", trump="Clubs") is False

def test_recommend_card_play_leads_highest_when_leading():
    hand = [("9", "Spades"), ("A", "Spades")]
    result = recommend_card_play(hand, trick_so_far=[], trump="Spades", led_suit=None)
    assert result == ("A", "Spades")

def test_recommend_card_play_wins_as_cheaply_as_possible():
    hand = [("9", "Hearts"), ("A", "Hearts")]
    result = recommend_card_play(hand, trick_so_far=[("10", "Hearts")], trump="Spades", led_suit="Hearts")
    assert result == ("A", "Hearts")

def test_recommend_card_play_throws_lowest_when_cannot_win():
    hand = [("9", "Hearts"), ("10", "Hearts")]
    result = recommend_card_play(hand, trick_so_far=[("A", "Hearts")], trump="Spades", led_suit="Hearts")
    assert result == ("9", "Hearts")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'legal_plays'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (32 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add legal-play checking and card-play AI heuristic"
```

---

### Task 8: Trick orchestration and winner determination

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `effective_suit`, `card_strength` (Task 2), `legal_plays` (Task 7)
- Produces:
  - `determine_trick_winner(plays, trump) -> int` — `plays` is `list[tuple[int, tuple]]` of `(seat, card)` in play order; led suit is derived from `plays[0]`.
  - `play_trick(hands, leader_seat, trump, sitting_out_seat, decision_fns) -> tuple[int, list[tuple[int, tuple]]]` — returns `(winner_seat, plays)`. Mutates `hands` in place (removes played cards). `decision_fns[seat](hand, trick_so_far_cards, trump, led_suit) -> card`.

- [ ] **Step 1: Write the failing tests**

```python
from euchre import determine_trick_winner, play_trick

def test_determine_trick_winner_trump_beats_led_suit():
    plays = [(0, ("A", "Hearts")), (1, ("9", "Spades")), (2, ("K", "Hearts")), (3, ("10", "Hearts"))]
    assert determine_trick_winner(plays, trump="Spades") == 1

def test_determine_trick_winner_highest_of_led_suit_when_no_trump():
    plays = [(0, ("9", "Hearts")), (1, ("A", "Hearts")), (2, ("K", "Diamonds")), (3, ("10", "Hearts"))]
    assert determine_trick_winner(plays, trump="Spades") == 1

def test_determine_trick_winner_left_bower_beats_other_trump():
    plays = [(0, ("A", "Spades")), (1, ("J", "Clubs")), (2, ("9", "Hearts")), (3, ("K", "Spades"))]
    assert determine_trick_winner(plays, trump="Spades") == 1

def test_play_trick_removes_played_cards_and_returns_winner():
    hands = [
        [("A", "Hearts")],
        [("9", "Spades")],
        [("K", "Hearts")],
        [("10", "Hearts")],
    ]
    def decision_fn(seat):
        return lambda hand, trick_so_far, trump, led_suit: hand[0]
    decision_fns = [decision_fn(s) for s in range(4)]
    winner, plays = play_trick(hands, leader_seat=0, trump="Spades", sitting_out_seat=None, decision_fns=decision_fns)
    assert winner == 1
    assert all(len(hand) == 0 for hand in hands)
    assert len(plays) == 4

def test_play_trick_skips_sitting_out_seat():
    hands = [
        [("9", "Hearts")],
        [],  # sitting out (loner's partner)
        [("A", "Hearts")],
        [("K", "Hearts")],
    ]
    decision_fns = [lambda hand, t, tr, l: hand[0] for _ in range(4)]
    winner, plays = play_trick(hands, leader_seat=0, trump="Spades", sitting_out_seat=1, decision_fns=decision_fns)
    seats_played = [seat for seat, card in plays]
    assert seats_played == [0, 2, 3]
    assert winner == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'determine_trick_winner'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (37 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add trick orchestration and winner determination"
```

---

### Task 9: Scoring

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Produces: `score_hand(tricks_by_team, making_team, went_alone) -> dict[int, int]` — `tricks_by_team` is `{0: count, 1: count}`; returns points earned this hand per team.

- [ ] **Step 1: Write the failing tests**

```python
from euchre import score_hand

def test_score_hand_one_point_for_three_or_four_tricks():
    result = score_hand({0: 3, 1: 2}, making_team=0, went_alone=False)
    assert result == {0: 1, 1: 0}

def test_score_hand_two_points_for_march():
    result = score_hand({0: 5, 1: 0}, making_team=0, went_alone=False)
    assert result == {0: 2, 1: 0}

def test_score_hand_four_points_for_lone_march():
    result = score_hand({0: 5, 1: 0}, making_team=0, went_alone=True)
    assert result == {0: 4, 1: 0}

def test_score_hand_euchre_gives_other_team_two_points():
    result = score_hand({0: 2, 1: 3}, making_team=0, went_alone=False)
    assert result == {0: 0, 1: 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'score_hand'`

- [ ] **Step 3: Write minimal implementation**

```python
# --- Scoring -------------------------------------------------------------

def score_hand(tricks_by_team, making_team, went_alone):
    other_team = 1 - making_team
    made_tricks = tricks_by_team[making_team]

    if made_tricks < 3:
        return {making_team: 0, other_team: 2}
    if made_tricks == 5:
        return {making_team: 4 if went_alone else 2, other_team: 0}
    return {making_team: 1, other_team: 0}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (41 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add hand scoring logic"
```

---

### Task 10: MMR persistence and rating math

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Produces: `load_mmr(path="mmr.json") -> dict`, `save_mmr(data, path="mmr.json") -> None`, `compute_quality_rate(decisions_log) -> float`, `update_mmr(mmr, quality_rate) -> int`, `difficulty_tier(mmr) -> str`

- [ ] **Step 1: Write the failing tests**

```python
import json
from euchre import load_mmr, save_mmr, compute_quality_rate, update_mmr, difficulty_tier

def test_load_mmr_returns_default_when_file_missing(tmp_path):
    path = tmp_path / "mmr.json"
    result = load_mmr(str(path))
    assert result == {"mmr": 1000, "games_played": 0}

def test_save_and_load_mmr_round_trip(tmp_path):
    path = tmp_path / "mmr.json"
    save_mmr({"mmr": 1234, "games_played": 5}, str(path))
    assert load_mmr(str(path)) == {"mmr": 1234, "games_played": 5}

def test_compute_quality_rate_counts_matches():
    log = [("order_up", "order_up"), ("pass", "order_up"), (("9", "Hearts"), ("9", "Hearts"))]
    assert compute_quality_rate(log) == 2 / 3

def test_compute_quality_rate_empty_log_is_neutral():
    assert compute_quality_rate([]) == 1.0

def test_update_mmr_rewards_above_baseline():
    assert update_mmr(1000, quality_rate=1.0) == 1000 + round(20 * (1.0 - 0.6))

def test_update_mmr_penalizes_below_baseline():
    assert update_mmr(1000, quality_rate=0.0) == 1000 + round(20 * (0.0 - 0.6))

def test_difficulty_tier_thresholds():
    assert difficulty_tier(800) == "easy"
    assert difficulty_tier(1200) == "medium"
    assert difficulty_tier(1600) == "hard"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_mmr'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (48 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add MMR persistence and rating calculation"
```

---

### Task 11: Difficulty mistake-rate wrapper and AI decision functions

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `recommend_bid_action`, `recommend_discard` (Task 5), `recommend_card_play`, `legal_plays` (Task 7)
- Produces: `MISTAKE_RATES: dict[str, float]`, `apply_mistake(recommended, alternatives, mistake_rate, rng) -> object`, `make_ai_bid_decision_fn(mistake_rate, rng=random) -> callable`, `make_ai_card_decision_fn(mistake_rate, rng=random) -> callable`, `make_ai_discard_decision_fn(mistake_rate, rng=random) -> callable`

- [ ] **Step 1: Write the failing tests**

```python
import random
from euchre import apply_mistake, make_ai_bid_decision_fn, make_ai_card_decision_fn

def test_apply_mistake_returns_recommended_when_roll_is_high():
    rng = random.Random(0)
    rng.random = lambda: 0.99  # never mistakes
    result = apply_mistake("order_up", alternatives=["pass"], mistake_rate=0.5, rng=rng)
    assert result == "order_up"

def test_apply_mistake_returns_alternative_when_roll_is_low():
    rng = random.Random(0)
    rng.random = lambda: 0.01  # always mistakes
    rng.choice = lambda options: options[0]
    result = apply_mistake("order_up", alternatives=["pass"], mistake_rate=0.5, rng=rng)
    assert result == "pass"

def test_ai_bid_decision_fn_calls_recommend_bid_action_at_zero_mistake_rate():
    rng = random.Random(0)
    rng.random = lambda: 0.99
    decision_fn = make_ai_bid_decision_fn(mistake_rate=0.0, rng=rng)
    strong_hand = [("J", "Spades"), ("J", "Clubs"), ("A", "Spades"), ("K", "Spades"), ("9", "Hearts")]
    result = decision_fn(strong_hand, "Spades")
    assert result == "order_up_alone"

def test_ai_card_decision_fn_calls_recommend_card_play_at_zero_mistake_rate():
    rng = random.Random(0)
    rng.random = lambda: 0.99
    decision_fn = make_ai_card_decision_fn(mistake_rate=0.0, rng=rng)
    hand = [("9", "Spades"), ("A", "Spades")]
    result = decision_fn(hand, [], "Spades", None)
    assert result == ("A", "Spades")

def test_ai_discard_decision_fn_calls_recommend_discard_at_zero_mistake_rate():
    from euchre import make_ai_discard_decision_fn
    rng = random.Random(0)
    rng.random = lambda: 0.99
    decision_fn = make_ai_discard_decision_fn(mistake_rate=0.0, rng=rng)
    hand = [("9", "Hearts"), ("A", "Spades"), ("J", "Spades"), ("Q", "Diamonds"), ("K", "Clubs"), ("10", "Hearts")]
    result = decision_fn(hand, trump="Spades")
    assert result == ("9", "Hearts")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'apply_mistake'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (53 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add difficulty mistake-rate wrapper and AI decision functions"
```

---

### Task 12: Human decision functions with oracle logging and terminal I/O

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: `recommend_bid_action`, `recommend_discard` (Task 5), `recommend_card_play`, `legal_plays` (Task 7)
- Produces: `make_human_bid_decision_fn(decisions_log) -> callable`, `make_human_card_decision_fn(decisions_log) -> callable`, `make_human_discard_decision_fn(decisions_log) -> callable`
- All three use `input()` for the actual human choice, and silently append `(actual, recommended)` to `decisions_log` for later MMR scoring — the recommendation is never printed before the human decides.

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch
from euchre import make_human_bid_decision_fn, make_human_card_decision_fn

def test_human_bid_decision_fn_round1_logs_recommendation(monkeypatch):
    decisions_log = []
    monkeypatch.setattr("builtins.input", lambda prompt="": "pass")
    decision_fn = make_human_bid_decision_fn(decisions_log)
    weak_hand = [("9", "Hearts"), ("10", "Diamonds"), ("Q", "Clubs"), ("9", "Diamonds"), ("K", "Hearts")]
    result = decision_fn(weak_hand, "Spades")
    assert result == "pass"
    assert decisions_log == [("pass", "pass")]

def test_human_card_decision_fn_logs_recommendation(monkeypatch):
    decisions_log = []
    hand = [("9", "Spades"), ("A", "Spades")]
    monkeypatch.setattr("builtins.input", lambda prompt="": "A Spades")
    decision_fn = make_human_card_decision_fn(decisions_log)
    result = decision_fn(hand, [], "Spades", None)
    assert result == ("A", "Spades")
    assert decisions_log == [(("A", "Spades"), ("A", "Spades"))]

def test_human_discard_decision_fn_logs_recommendation(monkeypatch):
    from euchre import make_human_discard_decision_fn
    decisions_log = []
    hand = [("9", "Hearts"), ("A", "Spades"), ("J", "Spades"), ("Q", "Diamonds"), ("K", "Clubs"), ("10", "Hearts")]
    monkeypatch.setattr("builtins.input", lambda prompt="": "9 Hearts")
    decision_fn = make_human_discard_decision_fn(decisions_log)
    result = decision_fn(hand, trump="Spades")
    assert result == ("9", "Hearts")
    assert decisions_log == [(("9", "Hearts"), ("9", "Hearts"))]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_human_bid_decision_fn'`

- [ ] **Step 3: Write minimal implementation**

```python
# --- Human decision functions (terminal I/O + oracle logging) --------------

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
            actual = "pass" if raw == "pass" else (raw, False)
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
        raw = input("Play a card (rank suit): ").strip().split()
        actual = (raw[0], raw[1])
        decisions_log.append((actual, recommended))
        return actual
    return decision_fn


def make_human_discard_decision_fn(decisions_log):
    def decision_fn(hand, trump):
        recommended = recommend_discard(hand, trump)
        print(f"Your hand after picking up the up-card: {hand}")
        raw = input("Discard a card (rank suit): ").strip().split()
        actual = (raw[0], raw[1])
        decisions_log.append((actual, recommended))
        return actual
    return decision_fn
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (56 passed)

- [ ] **Step 5: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Add human decision functions with oracle logging"
```

---

### Task 13: Full hand and game loop integration

**Files:**
- Modify: `euchre.py`
- Test: `tests/test_euchre.py`

**Interfaces:**
- Consumes: everything from Tasks 1-12
- Produces: `play_hand(hands, dealer_seat, up_card, hidden_kitty, bid_decision_fns, card_decision_fns, discard_decision_fns) -> tuple[dict[int,int], int, bool] | None`, `play_game(bid_decision_fns, card_decision_fns, discard_decision_fns) -> int` (returns winning team), `main()`

`play_hand` returns `(points_by_team, making_team, went_alone)`, or `None` if the hand was a redeal (all four passed both rounds with `stick_the_dealer=False`). Note `play_hand` uses `discard_decision_fns` (Tasks 11/12), not `card_decision_fns`, for the dealer's post-pickup discard — `recommend_card_play` picks the *best* card to play, which is the wrong direction for a discard, so a dedicated `recommend_discard`-backed function is used instead.

- [ ] **Step 1: Write the failing test**

```python
from euchre import play_hand, recommend_card_play, recommend_discard

def test_play_hand_scores_a_full_hand_deterministically():
    # Team 0 = seats 0,2 ; Team 1 = seats 1,3. Seat 0 orders up Spades and the
    # team runs the table (march) by always playing their highest legal card.
    hands = [
        [("J", "Spades"), ("J", "Clubs"), ("A", "Spades"), ("K", "Spades"), ("Q", "Spades")],
        [("9", "Hearts"), ("10", "Hearts"), ("Q", "Hearts"), ("K", "Hearts"), ("A", "Hearts")],
        [("9", "Diamonds"), ("10", "Diamonds"), ("Q", "Diamonds"), ("K", "Diamonds"), ("A", "Diamonds")],
        [("9", "Clubs"), ("10", "Clubs"), ("Q", "Clubs"), ("K", "Clubs"), ("A", "Clubs")],
    ]
    up_card = ("9", "Spades")
    hidden_kitty = [("9", "Hearts"), ("9", "Diamonds"), ("9", "Clubs")]  # unused once bidding resolves

    bid_decision_fns = [
        lambda hand, s: "order_up",  # seat 0 orders up
        lambda hand, s: "pass",
        lambda hand, s: "pass",
        lambda hand, s: "pass",
    ]
    card_decision_fns = [lambda hand, trick, trump, led: recommend_card_play(hand, trick, trump, led) for _ in range(4)]
    discard_decision_fns = [lambda hand, trump: recommend_discard(hand, trump) for _ in range(4)]

    result = play_hand(hands, dealer_seat=3, up_card=up_card, hidden_kitty=hidden_kitty,
                        bid_decision_fns=bid_decision_fns, card_decision_fns=card_decision_fns,
                        discard_decision_fns=discard_decision_fns)
    assert result is not None
    points_by_team, making_team, went_alone = result
    assert making_team == 0
    assert went_alone is False
    assert points_by_team[0] == 2  # march: seat 0's team holds all the trump/high cards
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_euchre.py -v`
Expected: FAIL with `ImportError: cannot import name 'play_hand'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_euchre.py -v`
Expected: PASS (57 passed)

- [ ] **Step 5: Manual smoke test**

Run: `python euchre.py`
Play through at least one full hand as the human (seat 0), entering bidding and card choices when prompted. Confirm: the hand resolves, points are scored and printed, and an `mmr.json` file appears in the project directory with an updated rating after the game ends (or interrupt after one hand completes if a full game to 10 takes too long to play manually).

- [ ] **Step 6: Commit**

```bash
git add euchre.py tests/test_euchre.py
git commit -m "Wire up full hand and game loop with MMR and difficulty"
```

---

## Self-Review Notes

- **Spec coverage:** deck/trump (Tasks 1-2), dealing (Task 3), dealer pick-up/discard + farmer's hand (Task 4), bidding heuristic + discard heuristic (Task 5), bidding orchestration incl. stick-the-dealer (Task 6), card-play legality/heuristic (Task 7), trick-play incl. going-alone seat-skipping (Task 8), scoring incl. lone march (Task 9), MMR persistence/math (Task 10), difficulty mistake-rate incl. discard (Task 11), human I/O + oracle logging incl. discard (Task 12), full integration (Task 13) — all spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO; every step has runnable code.
- **Type consistency:** `decision_fns` signatures are consistent across Tasks 6, 7, 8, 11, 12, 13 (`bid_decision_fn(hand, turned_suit_or_available, must_call=False)`, `card_decision_fn(hand, trick_so_far, trump, led_suit)`, `discard_decision_fn(hand, trump)`). `TEAM_OF_SEAT`, `RULES`, `MISTAKE_RATES` are defined once (Tasks 1, 11, 13) and reused, not redefined.
- **Caught during self-review:** the first draft of Task 13 reused `recommend_card_play`/`card_decision_fns` for the dealer's discard, which would discard the *best* card instead of the worst. Fixed by adding a dedicated `recommend_discard` (Task 5) plus `make_ai_discard_decision_fn`/`make_human_discard_decision_fn` (Tasks 11/12), threaded through `play_hand` and `play_game` as a separate `discard_decision_fns` list. Also simplified Task 13's round-2 bidding call — the human/AI bid decision functions already accept `(hand, turned_suit_or_available, must_call=False)`, matching `run_round2_bidding`'s 3-argument call directly, so the extra lambda-wrapping layer originally drafted was removed as dead weight.
- **Farmer's hand and going-alone in `play_hand`:** this first cut of Task 13 wires up the core round1/round2/trick/scoring path and going-alone's seat-skipping, but does not yet call `is_farmers_hand`/`swap_farmers_hand` from Task 4. If `RULES["farmers_hand"]` is `True`, add a pre-bidding step in `play_hand` that checks each non-dealer seat with `is_farmers_hand` and, if the human, prompts whether to swap (via a new small human-facing prompt) or if AI, always swaps when eligible — this is a small follow-up addition to Task 13's `play_hand`, not a new task, since it only affects the one function.
