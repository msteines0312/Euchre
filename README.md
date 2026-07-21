# Euchre Terminal Game
A playable terminal implementation of Euchre with AI opponents and a persistent skill-rating system, built to learn the rules while writing readable, well-tested code.

## Tech Stack
- Python (standard library only, no dependencies to run the game)
- pytest for testing

## How to Run
1. Clone the repo and `cd` into it.
2. (Optional, only needed for tests) Install pytest: `pip install pytest`
3. Play the game: `python euchre.py`
4. Run the test suite: `pytest tests/test_euchre.py`

## Key Features
- Full bower-ranking trump logic (right bower, left bower, and the same-color-suit rule) implemented as pure functions and covered by dedicated tests
- Configurable house rules: going alone, stick-the-dealer, and farmer's hand, toggled through a single `RULES` dictionary
- AI opponents driven by a shared heuristic function, so the same "sound play" logic powers the AI's decisions, the difficulty mistake rate, and the scoring oracle
- Adjustable difficulty (easy/medium/hard) that controls how often the AI deviates from the recommended play
- A persistent MMR system (`mmr.json`) that silently compares your bidding and card-play decisions to the same AI heuristic, then adjusts your rating and future difficulty based on how closely you matched sound play
- Trick-by-trick print output so a human player can follow trump, every card played, who won each trick, and the running score

## What I Learned
Building the shared heuristic that powers both the AI and the "oracle" grading system taught me how much cleaner it is to reuse one source of truth instead of writing separate logic for "what the AI does" and "what counts as a good decision." I also got a lot more comfortable with test-driven development, writing deterministic tests around card games that otherwise rely on random shuffling.
