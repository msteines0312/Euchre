// Euchre rules engine — a direct JS port of euchre.py's pure functions.
// Cards are [rank, suit] pairs. Keep this file free of DOM/UI code so the
// rules stay independently testable, same as the Python original.

const SUITS = ["Spades", "Hearts", "Diamonds", "Clubs"];
const RANKS = ["9", "10", "J", "Q", "K", "A"];
const RANK_ORDER = { "9": 0, "10": 1, "J": 2, "Q": 3, "K": 4, "A": 5 };
const SAME_COLOR = { Spades: "Clubs", Clubs: "Spades", Hearts: "Diamonds", Diamonds: "Hearts" };
const SUIT_SYMBOL = { Spades: "♠", Hearts: "♥", Diamonds: "♦", Clubs: "♣" };
const SUIT_COLOR = { Spades: "black", Clubs: "black", Hearts: "red", Diamonds: "red" };
const TEAM_OF_SEAT = { 0: 0, 2: 0, 1: 1, 3: 1 };

const DEFAULT_RULES = {
  allowGoingAlone: true,
  stickTheDealer: false,
  farmersHand: false,
};

function cardKey(card) {
  return card[0] + "-" + card[1];
}

function cardsEqual(a, b) {
  return a[0] === b[0] && a[1] === b[1];
}

function createDeck() {
  const deck = [];
  for (const suit of SUITS) {
    for (const rank of RANKS) {
      deck.push([rank, suit]);
    }
  }
  return deck;
}

function shuffle(deck, rng = Math.random) {
  const arr = deck.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// --- Trump / bower ranking ---------------------------------------------

function effectiveSuit(card, trump) {
  const [rank, suit] = card;
  if (rank === "J" && SAME_COLOR[suit] === trump) return trump;
  return suit;
}

function cardStrength(card, trump) {
  const [rank, suit] = card;
  if (rank === "J" && suit === trump) return 31; // right bower
  if (rank === "J" && SAME_COLOR[suit] === trump) return 30; // left bower
  if (effectiveSuit(card, trump) === trump) return 20 + RANK_ORDER[rank];
  return RANK_ORDER[rank];
}

// --- Dealing -------------------------------------------------------------

function dealHands(deck) {
  const hands = [0, 1, 2, 3].map((i) => deck.slice(i * 5, (i + 1) * 5));
  const upCard = deck[20];
  const hiddenKitty = deck.slice(21, 24);
  return { hands, upCard, hiddenKitty };
}

// --- Dealer pick-up, discard, farmer's hand -----------------------------

function pickUpCard(dealerHand, upCard) {
  return [...dealerHand, upCard];
}

function discard(hand, cardToDiscard) {
  const idx = hand.findIndex((c) => cardsEqual(c, cardToDiscard));
  const newHand = hand.slice();
  newHand.splice(idx, 1);
  return newHand;
}

function isFarmersHand(hand) {
  return hand.every(([rank]) => rank === "9" || rank === "10");
}

function swapFarmersHand(hand, keepCards, hiddenKitty) {
  return [...keepCards, ...hiddenKitty];
}

// --- Bidding AI heuristic ------------------------------------------------

const ORDER_UP_THRESHOLD = 45;
const ALONE_THRESHOLD = 80;

function handTrumpStrength(hand, trump) {
  const trumpCards = hand.filter((c) => effectiveSuit(c, trump) === trump);
  return trumpCards.length * 10 + trumpCards.reduce((sum, c) => sum + cardStrength(c, trump), 0);
}

// round 1: recommendBidAction(hand, {roundNum: 1, isDealer, turnedSuit}) -> "pass"|"order_up"|"order_up_alone"
// round 2: recommendBidAction(hand, {roundNum: 2, isDealer, availableSuits}) -> "pass"|{suit, alone}
function recommendBidAction(hand, { roundNum, isDealer, turnedSuit = null, availableSuits = null }) {
  if (roundNum === 1) {
    const strength = handTrumpStrength(hand, turnedSuit);
    if (strength >= ALONE_THRESHOLD) return "order_up_alone";
    if (strength >= ORDER_UP_THRESHOLD) return "order_up";
    return "pass";
  }

  let bestSuit = null;
  let bestStrength = -1;
  for (const suit of availableSuits) {
    const strength = handTrumpStrength(hand, suit);
    if (strength > bestStrength) {
      bestSuit = suit;
      bestStrength = strength;
    }
  }
  if (bestStrength >= ALONE_THRESHOLD) return { suit: bestSuit, alone: true };
  if (bestStrength >= ORDER_UP_THRESHOLD || isDealer) return { suit: bestSuit, alone: false };
  return "pass";
}

function recommendDiscard(hand, trump) {
  return hand.reduce((weakest, c) => (cardStrength(c, trump) < cardStrength(weakest, trump) ? c : weakest));
}

// --- Card-play legality and AI heuristic ---------------------------------

function legalPlays(hand, ledSuit, trump) {
  if (ledSuit === null) return hand.slice();
  const following = hand.filter((c) => effectiveSuit(c, trump) === ledSuit);
  return following.length ? following : hand.slice();
}

function isLegalPlay(card, hand, ledSuit, trump) {
  return legalPlays(hand, ledSuit, trump).some((c) => cardsEqual(c, card));
}

// plays: array of {seat, card} played so far this trick, in play order.
// Returns the seat currently holding the best card, or null if plays is empty.
function currentTrickLeader(plays, trump, ledSuit) {
  if (!plays.length) return null;
  function rank(play) {
    const card = play.card;
    if (effectiveSuit(card, trump) === trump) return [2, cardStrength(card, trump)];
    if (card[1] === ledSuit) return [1, cardStrength(card, trump)];
    return [0, 0];
  }
  let winner = plays[0];
  let winnerRank = rank(winner);
  for (const play of plays.slice(1)) {
    const r = rank(play);
    if (r[0] > winnerRank[0] || (r[0] === winnerRank[0] && r[1] > winnerRank[1])) {
      winner = play;
      winnerRank = r;
    }
  }
  return winner.seat;
}

// trickPlays: array of {seat, card} already played this trick (not including `seat`).
// seat: the seat about to play (needed to tell a winning partner from a winning opponent).
function recommendCardPlay(hand, trickPlays, trump, ledSuit, seat = null) {
  const options = legalPlays(hand, ledSuit, trump);
  if (ledSuit === null) {
    return options.reduce((best, c) => (cardStrength(c, trump) > cardStrength(best, trump) ? c : best));
  }

  const leaderSeat = currentTrickLeader(trickPlays, trump, ledSuit);
  const partnerIsWinning = leaderSeat !== null && seat !== null && TEAM_OF_SEAT[leaderSeat] === TEAM_OF_SEAT[seat];
  if (partnerIsWinning) {
    // Your partner already holds the best card -- don't waste strength beating your own team.
    return options.reduce((worst, c) => (cardStrength(c, trump) < cardStrength(worst, trump) ? c : worst));
  }

  let winningOptions = options;
  if (trickPlays.length) {
    const bestPlayed = Math.max(...trickPlays.map((p) => cardStrength(p.card, trump)));
    winningOptions = options.filter((c) => cardStrength(c, trump) > bestPlayed);
  }
  const pool = winningOptions.length ? winningOptions : options;
  return pool.reduce((best, c) => (cardStrength(c, trump) < cardStrength(best, trump) ? c : best));
}

// --- Trick orchestration --------------------------------------------------

// plays: array of {seat, card} in play order.
function determineTrickWinner(plays, trump) {
  const ledSuit = effectiveSuit(plays[0].card, trump);
  return currentTrickLeader(plays, trump, ledSuit);
}

// --- Scoring ---------------------------------------------------------------

function scoreHand(tricksByTeam, makingTeam, wentAlone) {
  const otherTeam = 1 - makingTeam;
  const madeTricks = tricksByTeam[makingTeam];
  if (madeTricks < 3) return { [makingTeam]: 0, [otherTeam]: 2 };
  if (madeTricks === 5) return { [makingTeam]: wentAlone ? 4 : 2, [otherTeam]: 0 };
  return { [makingTeam]: 1, [otherTeam]: 0 };
}

export {
  SUITS,
  RANKS,
  RANK_ORDER,
  SAME_COLOR,
  SUIT_SYMBOL,
  SUIT_COLOR,
  TEAM_OF_SEAT,
  DEFAULT_RULES,
  cardKey,
  cardsEqual,
  createDeck,
  shuffle,
  effectiveSuit,
  cardStrength,
  dealHands,
  pickUpCard,
  discard,
  isFarmersHand,
  swapFarmersHand,
  handTrumpStrength,
  recommendBidAction,
  recommendDiscard,
  legalPlays,
  isLegalPlay,
  recommendCardPlay,
  currentTrickLeader,
  determineTrickWinner,
  scoreHand,
};
