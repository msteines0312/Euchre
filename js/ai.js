// AI decision-making: wraps the "recommended" heuristics from engine.js with a
// tunable mistake rate, and tracks a persistent MMR/difficulty rating in
// localStorage (a browser stand-in for euchre.py's mmr.json).
//
// MMR is stored as a single "table" keyed by player name, so the same browser
// can hold separate profiles for each name typed into the name field —
// entering a name looks up (or creates) that name's own MMR record.

import {
  recommendBidAction,
  recommendDiscard,
  recommendCardPlay,
  legalPlays,
  cardsEqual,
} from "./engine.js";

const MISTAKE_RATES = { easy: 0.3, medium: 0.15, hard: 0.0 };
const K = 20;
const BASELINE = 0.6;
const DEFAULT_MMR = { mmr: 1000, gamesPlayed: 0 };
const PLAYERS_TABLE_KEY = "euchre-players-v1";

function normalizePlayerKey(name) {
  return name.trim().toLowerCase();
}

function loadPlayersTable() {
  try {
    const raw = localStorage.getItem(PLAYERS_TABLE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function savePlayersTable(table) {
  try {
    localStorage.setItem(PLAYERS_TABLE_KEY, JSON.stringify(table));
  } catch {
    // localStorage unavailable (private browsing, etc.) — silently skip persistence.
  }
}

// Looks up `name`'s MMR record, creating a fresh default one if this is a new name.
function loadMmr(name) {
  const table = loadPlayersTable();
  const record = table[normalizePlayerKey(name)];
  return record ? { ...DEFAULT_MMR, ...record } : { ...DEFAULT_MMR };
}

function saveMmr(name, data) {
  const table = loadPlayersTable();
  table[normalizePlayerKey(name)] = data;
  savePlayersTable(table);
}

function computeQualityRate(decisionsLog) {
  if (!decisionsLog.length) return 1.0;
  const matches = decisionsLog.filter(([actual, recommended]) => actual === recommended).length;
  return matches / decisionsLog.length;
}

function updateMmr(mmr, qualityRate) {
  return mmr + Math.round(K * (qualityRate - BASELINE));
}

function difficultyTier(mmr) {
  if (mmr < 900) return "easy";
  if (mmr < 1500) return "medium";
  return "hard";
}

function pickRandom(rng, options) {
  return options[Math.floor(rng() * options.length)];
}

function applyMistake(recommended, alternatives, mistakeRate, rng = Math.random) {
  if (alternatives.length && rng() < mistakeRate) return pickRandom(rng, alternatives);
  return recommended;
}

// bidArgs: round 1 -> {roundNum:1, turnedSuit}; round 2 -> {roundNum:2, availableSuits, isDealer}
function makeAiBidDecisionFn(mistakeRate, rng = Math.random) {
  return (hand, bidArgs) => {
    const recommended = recommendBidAction(hand, { isDealer: false, ...bidArgs });
    let alternatives = [];
    if (bidArgs.roundNum === 1) {
      alternatives = recommended !== "pass" ? ["pass"] : [];
    } else {
      alternatives = recommended !== "pass" && !bidArgs.isDealer ? ["pass"] : [];
    }
    return applyMistake(recommended, alternatives, mistakeRate, rng);
  };
}

function makeAiCardDecisionFn(mistakeRate, rng = Math.random) {
  return (hand, trickPlays, trump, ledSuit, seat = null) => {
    const recommended = recommendCardPlay(hand, trickPlays, trump, ledSuit, seat);
    const options = legalPlays(hand, ledSuit, trump);
    const alternatives = options.filter((c) => !cardsEqual(c, recommended));
    return applyMistake(recommended, alternatives, mistakeRate, rng);
  };
}

function makeAiDiscardDecisionFn(mistakeRate, rng = Math.random) {
  return (hand, trump) => {
    const recommended = recommendDiscard(hand, trump);
    const alternatives = hand.filter((c) => !cardsEqual(c, recommended));
    return applyMistake(recommended, alternatives, mistakeRate, rng);
  };
}

export {
  MISTAKE_RATES,
  loadMmr,
  saveMmr,
  computeQualityRate,
  updateMmr,
  difficultyTier,
  applyMistake,
  makeAiBidDecisionFn,
  makeAiCardDecisionFn,
  makeAiDiscardDecisionFn,
};
