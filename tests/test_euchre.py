import random
from euchre import create_deck, deal_hands, SUITS, RANKS, effective_suit, card_strength, pick_up_card, discard, is_farmers_hand, swap_farmers_hand, recommend_bid_action, recommend_discard, run_round1_bidding, run_round2_bidding, legal_plays, is_legal_play, recommend_card_play, determine_trick_winner, play_trick, score_hand, load_mmr, save_mmr, compute_quality_rate, update_mmr, difficulty_tier, apply_mistake, make_ai_bid_decision_fn, make_ai_card_decision_fn, make_ai_discard_decision_fn

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

def test_create_deck_has_24_unique_cards():
    deck = create_deck()
    assert len(deck) == 24
    assert len(set(deck)) == 24

def test_create_deck_has_all_suits_and_ranks():
    deck = create_deck()
    for suit in SUITS:
        for rank in RANKS:
            assert (rank, suit) in deck

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

def test_is_farmers_hand_false_for_wrong_size_hand():
    short_hand = [("9", "Hearts"), ("10", "Hearts"), ("9", "Spades")]
    assert is_farmers_hand(short_hand) is False

def test_swap_farmers_hand_combines_kept_cards_and_kitty():
    hand = [("9", "Hearts"), ("10", "Hearts"), ("9", "Spades"), ("10", "Spades"), ("9", "Clubs")]
    keep_cards = [("9", "Hearts"), ("10", "Hearts")]
    hidden_kitty = [("A", "Clubs"), ("K", "Diamonds"), ("Q", "Spades")]
    new_hand = swap_farmers_hand(hand, keep_cards, hidden_kitty)
    assert len(new_hand) == 5
    assert sorted(new_hand) == sorted(keep_cards + hidden_kitty)

def test_recommend_pass_on_weak_hand_round_1():
    weak_hand = [("9", "Hearts"), ("10", "Diamonds"), ("Q", "Clubs"), ("9", "Diamonds"), ("K", "Hearts")]
    assert recommend_bid_action(weak_hand, round_num=1, is_dealer=False, turned_suit="Spades") == "pass"

def test_recommend_order_up_on_strong_hand_round_1():
    strong_hand = [("J", "Spades"), ("J", "Clubs"), ("A", "Spades"), ("K", "Spades"), ("9", "Hearts")]
    assert recommend_bid_action(strong_hand, round_num=1, is_dealer=False, turned_suit="Spades") == "order_up_alone"

def test_recommend_pass_round_2_on_weak_hand():
    weak_hand = [("9", "Hearts"), ("9", "Diamonds"), ("9", "Clubs"), ("10", "Spades"), ("K", "Spades")]
    result = recommend_bid_action(weak_hand, round_num=2, is_dealer=False, available_suits=["Hearts", "Diamonds", "Clubs"])
    assert result == "pass"

def test_recommend_call_best_suit_round_2():
    hand = [("J", "Diamonds"), ("J", "Hearts"), ("A", "Diamonds"), ("K", "Diamonds"), ("9", "Clubs")]
    result = recommend_bid_action(hand, round_num=2, is_dealer=False, available_suits=["Hearts", "Diamonds", "Clubs"])
    assert result[0] == "Diamonds"

def test_recommend_discard_picks_weakest_card():
    hand = [("9", "Hearts"), ("A", "Spades"), ("J", "Spades"), ("Q", "Diamonds"), ("K", "Clubs"), ("10", "Hearts")]
    # trump is Spades: A/J-Spades are strong trump, the rest are weak off-suit cards.
    # 9-Hearts is the single weakest card by card_strength.
    assert recommend_discard(hand, trump="Spades") == ("9", "Hearts")

def test_recommend_bid_action_forces_call_when_dealer_stuck():
    weak_hand = [("9", "Hearts"), ("9", "Diamonds"), ("9", "Clubs"), ("10", "Spades"), ("K", "Spades")]
    available_suits = ["Hearts", "Diamonds", "Clubs"]
    assert recommend_bid_action(weak_hand, round_num=2, is_dealer=False, available_suits=available_suits) == "pass"
    forced_result = recommend_bid_action(weak_hand, round_num=2, is_dealer=True, available_suits=available_suits)
    assert forced_result != "pass"
    assert forced_result[1] is False  # not alone -- hand isn't strong enough for that

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


# --- MMR / difficulty tests ------------------------------------------------

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
    assert difficulty_tier(900) == "medium"
    assert difficulty_tier(1200) == "medium"
    assert difficulty_tier(1500) == "hard"
    assert difficulty_tier(1600) == "hard"


# --- Difficulty mistake-rate wrapper -----------------------------------

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
    rng = random.Random(0)
    rng.random = lambda: 0.99
    decision_fn = make_ai_discard_decision_fn(mistake_rate=0.0, rng=rng)
    hand = [("9", "Hearts"), ("A", "Spades"), ("J", "Spades"), ("Q", "Diamonds"), ("K", "Clubs"), ("10", "Hearts")]
    result = decision_fn(hand, trump="Spades")
    assert result == ("9", "Hearts")
