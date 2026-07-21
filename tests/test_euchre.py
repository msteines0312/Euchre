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
