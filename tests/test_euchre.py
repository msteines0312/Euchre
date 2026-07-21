from euchre import create_deck, deal_hands, SUITS, RANKS, effective_suit, card_strength

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
