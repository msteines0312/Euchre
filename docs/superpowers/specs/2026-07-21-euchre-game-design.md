# Euchre Terminal Game - Design Spec

## Purpose

A playable terminal Euchre game so the user can learn the rules by playing
against AI opponents, and can read/tweak the code easily as they learn.
Portfolio-quality code: readable, small functions, no over-engineering.

## Scope

Single project, built in phases:
1. Cards, deck, trump/bower ranking
2. Bidding (both rounds, rule variants)
3. Trick-play (including going alone)
4. Scoring and game loop
5. MMR / difficulty system

## File Layout

- `euchre.py` - single file, top to bottom, organized into clearly
  commented sections (cards/deck, trump ranking, dealing, bidding, AI
  heuristics, trick-play, scoring, MMR, main game loop).
- `mmr.json` - auto-created local data file storing persistent rating:
  `{"mmr": 1000, "games_played": 0}`.
- `tests/test_euchre.py` - pytest cases, added phase by phase.

Cards are represented as plain tuples, e.g. `("J", "Spades")` - simplest
to read/print/compare, no need for a `Card` class at this scale.

## Cards, Deck, and Trump/Bower Ranking

- 24-card deck: ranks `9,10,J,Q,K,A` x suits `Spades,Hearts,Diamonds,Clubs`.
- A color-pair dict maps each suit to its same-color partner
  (`Spades<->Clubs`, `Hearts<->Diamonds`) - this drives the left bower rule.
- `effective_suit(card, trump)`: returns what suit a card counts as for
  follow-suit purposes. Normally the card's own suit, except the left
  bower (the `J` of the same color as trump) counts as the trump suit.
- `card_strength(card, trump)`: returns a comparable number encoding the
  full order - right bower (highest) > left bower > other trump (A high
  to 9 low) > non-trump cards ranked within their own suit (A high to 9
  low, always weaker than any trump).

## Configurable Rule Variants

```python
RULES = {
    "allow_going_alone": True,
    "stick_the_dealer": False,   # dealer must call trump in round 2, no redeal
    "farmers_hand": False,       # weak-hand swap, see below
}
```

- **Going alone**: during either bidding round, whoever orders up / calls
  trump can declare "alone" instead of a plain call. Partner's cards are
  set aside for the hand; trick-play becomes 3-handed, turn order skips
  the sitting-out seat. Scoring: loner taking all 5 tricks is a march for
  **4 points** (instead of 2); 3-4 tricks is still 1 point; euchre still
  gives the other team 2 points.
- **Stick the dealer**: in round 2, if `True`, the dealer cannot pass and
  must name a suit. If `False` (default), two full passes trigger a
  redeal.
- **Farmer's hand**: any non-dealer whose hand is all 9s/10s (no face
  cards) may, before round 1 bidding starts, swap 3 of their 5 cards for
  the 3 hidden kitty cards, choosing which 2 of their original 5 to keep.
  (The deck only leaves 4 undealt cards after dealing - 1 turned face-up
  for bidding, 3 hidden in the kitty - so a full 5-for-5 swap isn't
  possible without touching the up-card or forcing a redeal; this 3-for-3
  version keeps the up-card and bidding mechanics untouched.)

## Bidding

- **Round 1**: going around from left of dealer, each player may order up
  the turned suit or pass. If ordered up (plain or alone), dealer picks up
  the up-card and discards one card back to the kitty.
- **Round 2**: if everyone passes round 1, going around again, each player
  may call any suit other than the turned-down suit, or pass (unless
  `stick_the_dealer` forces the dealer to call).

## AI Heuristics (Shared Logic)

One function each, reused three ways (AI decisions, difficulty mistake
rates, and the MMR oracle):

```python
def recommend_bid_action(hand, turned_card, round_num, is_dealer):
    """Returns the 'sound' bidding action for this hand/situation."""

def recommend_card_play(hand, trick_so_far, trump, led_suit):
    """Returns the 'sound' card to play for this situation."""
```

- `recommend_bid_action`: scores trump-suit strength (trump count,
  presence of bowers, off-suit aces) against a threshold; returns
  order-up/call/pass, and "alone" if the hand is strong enough (e.g. both
  bowers plus the ace).
- `recommend_card_play`: play highest legal card if you can and should win
  the trick, lowest legal card if not; must-follow-suit enforced first.

**Three uses of each function:**
1. AI opponents' actual decisions - called directly.
2. Difficulty tiers - each AI seat has a `mistake_rate` (easy=30%,
   medium=15%, hard=0%) chance to ignore the recommendation and do
   something else instead. This is how "easy" AI plays worse without
   separate dumb logic.
3. MMR oracle - on the user's turns, the same function is called
   silently (never shown mid-hand) and compared against what the user
   actually chose.

## Trick-Play

- Left-of-dealer leads first trick; if that seat is sitting out (it's the
  partner of a lone hand), leadership skips to the next active seat.
- Each player must follow the suit led if able; `effective_suit()` handles
  the left-bower-counts-as-trump case.
- Highest `card_strength()` among cards that followed suit or trumped
  wins the trick; winner leads next. Five tricks per hand.

## Scoring

- Making team took 3-4 tricks -> 1 point
- Making team took all 5 (march) -> 2 points, or 4 points if it was a lone
  hand
- Making team took 0-2 tricks (euchred) -> other team gets 2 points
- First team to 10 points wins the game

## MMR / Difficulty System

- **Persistence** (`mmr.json`): `{"mmr": 1000, "games_played": 0}`, loaded
  at startup, saved after every hand.
- **Decision-quality scoring**: every bidding decision and card play the
  user personally makes is compared to `recommend_bid_action()` /
  `recommend_card_play()` for that exact situation. At hand's end:
  `quality_rate = matches / total_decisions`.
- **Rating update** (constants tunable at the top of the file):

```python
K = 20
BASELINE = 0.6  # matching the heuristic 60% of the time is "expected"
mmr += round(K * (quality_rate - BASELINE))
```

  Printed at hand's end, e.g.:
  `"Your decisions matched sound play 4/5 times. MMR: 1000 -> 1008 (+8)"`

- **Difficulty mapping** (also tunable constants):

```python
if mmr < 900: tier = "easy"
elif mmr < 1500: tier = "medium"
else: tier = "hard"
```

  This tier sets every AI seat's `mistake_rate` for that game. At startup
  the user is shown their current MMR/tier and can optionally override it
  for one session (e.g. force "easy" to relax).

## Testing Plan

`tests/test_euchre.py`, built up phase by phase alongside the code:

1. **Trump/bower ranking** - right bower > left bower > other trump >
   off-suit cards; `effective_suit` correctly reassigns the left bower.
2. **Bidding** - order-up/discard mechanics, round 2 restrictions (can't
   call the turned-down suit), stick-the-dealer forcing a call,
   farmer's-hand swap producing a valid 5-card hand.
3. **Trick-play** - follow-suit enforcement (including left bower as
   trump), correct trick winner determination, 3-handed rotation when
   someone goes alone.
4. **Scoring** - all point outcomes (1/2/4 point cases, euchre), game
   ending at 10.
5. **MMR** - quality_rate calculation, rating update formula, difficulty
   tier mapping.

Each test uses hand-constructed hands/tricks (no randomness) so results
are deterministic.
