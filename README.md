# Euchre
A playable implementation of Euchre with AI opponents and a persistent skill-rating system, available both as a terminal game and as a browser game hosted on GitHub Pages.

## Tech Stack
- Python (standard library only, no dependencies to run the terminal game)
- pytest for testing the Python rules engine
- Vanilla JavaScript (ES modules), HTML, and CSS for the browser version, no build step or frameworks
- Procedurally generated SVG playing cards, no image assets

## How to Run

**Terminal version:**
1. Clone the repo and `cd` into it.
2. (Optional, only needed for tests) Install pytest: `pip install pytest`
3. Play the game: `python euchre.py`
4. Run the test suite: `pytest tests/test_euchre.py`

**Browser version:**
1. Open `index.html` directly, or serve the repo root with any static file server (for example `python -m http.server`) and visit it in a browser.
2. Click "Deal Me In" and play. No installation or build step needed.
3. The live version is hosted on GitHub Pages directly from this repo's root.

## Key Features
- Full bower-ranking trump logic (right bower, left bower, and the same-color-suit rule) implemented as pure functions and covered by dedicated tests
- Configurable house rules: going alone, stick-the-dealer, and farmer's hand, toggled through a single `RULES` dictionary (Python) or a settings panel (browser)
- AI opponents driven by a shared heuristic function, so the same "sound play" logic powers the AI's decisions, the difficulty mistake rate, and the scoring oracle
- Adjustable difficulty (easy/medium/hard) that controls how often the AI deviates from the recommended play
- A persistent MMR system that silently compares your bidding and card-play decisions to the same AI heuristic, then adjusts your rating and future difficulty based on how closely you matched sound play (stored in `mmr.json` for the terminal game, in `localStorage` for the browser game)
- The browser version reimplements the same rules engine in JavaScript (`js/engine.js`) so the game runs entirely client-side on GitHub Pages, with an animated felt-table UI, bidding/discard overlays, and a mobile-responsive layout

## What I Learned
Building the shared heuristic that powers both the AI and the "oracle" grading system taught me how much cleaner it is to reuse one source of truth instead of writing separate logic for "what the AI does" and "what counts as a good decision." I also got a lot more comfortable with test-driven development, writing deterministic tests around card games that otherwise rely on random shuffling. Porting the same rules to JavaScript for the browser version reinforced how valuable it is to keep game logic as pure, side-effect-free functions: the trump ranking, legal-play, and scoring functions translated almost line-for-line, while the human-vs-AI turn orchestration had to be redesigned around Promises and DOM events instead of injectable Python callables.
