from euchre import create_deck, deal_hands, SUITS, RANKS, effective_suit, card_strength, pick_up_card, discard, is_farmers_hand, swap_farmers_hand, recommend_bid_action, recommend_discard

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
