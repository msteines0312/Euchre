// Game orchestration: wires the pure rules engine + AI to the DOM, driving
// deal -> bid round 1 -> (pickup/discard) -> bid round 2 -> 5 tricks ->
// score -> next hand -> game win. Human turns are awaited as Promises
// resolved by button/card clicks.

import * as E from "./engine.js";
import * as AI from "./ai.js";
import { renderCard } from "./cards.js";

const $ = (id) => document.getElementById(id);

const SEAT_NAMES = { 0: "You", 1: "East", 2: "North", 3: "West" };
const HAND_EL = { 0: $("hand-0"), 1: $("hand-1"), 2: $("hand-2"), 3: $("hand-3") };
const TRICKS_PILL = { 0: $("tricks-0"), 1: $("tricks-1"), 2: $("tricks-2"), 3: $("tricks-3") };
const TRICK_SLOT = { 0: $("trick-0"), 1: $("trick-1"), 2: $("trick-2"), 3: $("trick-3") };

const rules = { ...E.DEFAULT_RULES };
let difficultyOverride = "auto";
let mmrData = AI.loadMmr();
let decisionsLog = [];
let scores = { 0: 0, 1: 0 };
let dealerSeat = 0;
let hands = [[], [], [], []];
let sittingOutSeat = null;
let upCard = null;
let hiddenKitty = [];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function currentMistakeRate() {
  const tier = difficultyOverride === "auto" ? AI.difficultyTier(mmrData.mmr) : difficultyOverride;
  return AI.MISTAKE_RATES[tier];
}

function aiFns() {
  const rate = currentMistakeRate();
  return {
    bid: AI.makeAiBidDecisionFn(rate),
    card: AI.makeAiCardDecisionFn(rate),
    discard: AI.makeAiDiscardDecisionFn(rate),
  };
}

// ===== Toast / small messaging ============================================

let toastTimer = null;
function showToast(message, duration = 1800) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  if (duration > 0) toastTimer = setTimeout(() => el.classList.remove("show"), duration);
}
function hideToast() {
  $("toast").classList.remove("show");
}

// ===== Rendering helpers ===================================================

function clearEl(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function renderOpponentHand(seat, count) {
  const el = HAND_EL[seat];
  clearEl(el);
  for (let i = 0; i < count; i++) {
    const back = renderCard(null, { faceUp: false, className: "dealt-in" });
    back.style.animationDelay = `${i * 40}ms`;
    el.appendChild(back);
  }
}

function renderBottomHandStatic(hand) {
  const el = HAND_EL[0];
  clearEl(el);
  for (const card of hand) {
    el.appendChild(renderCard(card, { className: "dealt-in" }));
  }
}

// Renders the human hand with click-to-choose interaction. `filterFn(card)`
// marks cards as playable/selectable vs dimmed. Resolves with the chosen card.
function chooseCardFromHand(hand, filterFn, selectableClass = "playable") {
  return new Promise((resolve) => {
    const el = HAND_EL[0];
    clearEl(el);
    for (const card of hand) {
      const isChoosable = filterFn(card);
      const cardEl = renderCard(card, { className: isChoosable ? selectableClass : "unplayable" });
      if (isChoosable) {
        cardEl.setAttribute("role", "button");
        cardEl.setAttribute("tabindex", "0");
        cardEl.setAttribute("aria-label", `Play ${card[0]} of ${card[1]}`);
        const choose = () => resolve(card);
        cardEl.addEventListener("click", choose, { once: true });
        cardEl.addEventListener(
          "keydown",
          (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              choose();
            }
          },
          { once: true }
        );
      }
      el.appendChild(cardEl);
    }
  });
}

function updateScoreboard() {
  $("score-us").textContent = scores[0];
  $("score-them").textContent = scores[1];
}

function updateDifficultyChip() {
  const tier = difficultyOverride === "auto" ? AI.difficultyTier(mmrData.mmr) : difficultyOverride;
  $("difficulty-label").textContent = tier[0].toUpperCase() + tier.slice(1);
}

function updateDealerChip() {
  const chip = $("dealer-chip");
  const seatEl = document.getElementById(`seat-${dealerSeat}`);
  const centerRect = $("center-area").getBoundingClientRect();
  const seatRect = seatEl.getBoundingClientRect();
  chip.style.left = `${seatRect.left + seatRect.width / 2 - centerRect.left - 13}px`;
  chip.style.top = `${seatRect.top - centerRect.top - 13}px`;
}

function trumpSuitClass(suit) {
  return E.SUIT_COLOR[suit] === "red" ? "suit-red" : "suit-black";
}

// ===== Overlay dialog helpers ==============================================

function showOverlay(id) {
  $(id).classList.remove("hidden");
}
function hideOverlay(id) {
  $(id).classList.add("hidden");
}

function waitOnce(el, event = "click") {
  return new Promise((resolve) => el.addEventListener(event, resolve, { once: true }));
}

async function showBid1Modal(upCardShown) {
  const turnedSuit = upCardShown[1];
  $("bid1-suit-name").textContent = turnedSuit;
  $("bid1-suit-name").className = trumpSuitClass(turnedSuit);
  clearEl($("bid1-upcard"));
  $("bid1-upcard").appendChild(renderCard(upCardShown, {}));
  const aloneBtn = $("bid1-alone-btn");
  aloneBtn.style.display = rules.allowGoingAlone ? "" : "none";
  showOverlay("bid1-overlay");

  return new Promise((resolve) => {
    const orderBtn = $("bid1-order-btn");
    const passBtn = $("bid1-pass-btn");
    const cleanup = () => {
      orderBtn.removeEventListener("click", onOrder);
      aloneBtn.removeEventListener("click", onAlone);
      passBtn.removeEventListener("click", onPass);
      hideOverlay("bid1-overlay");
    };
    const onOrder = () => { cleanup(); resolve("order_up"); };
    const onAlone = () => { cleanup(); resolve("order_up_alone"); };
    const onPass = () => { cleanup(); resolve("pass"); };
    orderBtn.addEventListener("click", onOrder);
    aloneBtn.addEventListener("click", onAlone);
    passBtn.addEventListener("click", onPass);
  });
}

async function showBid2Modal(availableSuits, mustCall) {
  const grid = $("bid2-suit-grid");
  clearEl(grid);
  const passBtn = $("bid2-pass-btn");
  const aloneCheck = $("bid2-alone-check");
  aloneCheck.checked = false;
  passBtn.style.display = mustCall ? "none" : "";
  $("bid2-prompt").textContent = mustCall
    ? "You're stuck! You must name a suit."
    : "Call any suit other than the turned-down suit.";
  document.getElementById("bid2-alone-check").parentElement.style.display = rules.allowGoingAlone ? "" : "none";

  showOverlay("bid2-overlay");

  return new Promise((resolve) => {
    const cleanupFns = [];
    const cleanup = () => {
      cleanupFns.forEach((fn) => fn());
      hideOverlay("bid2-overlay");
    };
    for (const suit of availableSuits) {
      const btn = document.createElement("button");
      btn.className = "suit-btn";
      btn.innerHTML = `<span class="${trumpSuitClass(suit)}">${E.SUIT_SYMBOL[suit]}</span> ${suit}`;
      const onClick = () => {
        const alone = rules.allowGoingAlone && aloneCheck.checked;
        cleanup();
        resolve({ suit, alone });
      };
      btn.addEventListener("click", onClick);
      cleanupFns.push(() => btn.removeEventListener("click", onClick));
      grid.appendChild(btn);
    }
    const onPass = () => { cleanup(); resolve("pass"); };
    passBtn.addEventListener("click", onPass);
    cleanupFns.push(() => passBtn.removeEventListener("click", onPass));
  });
}

async function showDiscardOverlay(hand, trump) {
  showOverlay("discard-overlay");
  const el = $("discard-hand-cards");
  const sorted = hand.slice().sort((a, b) => E.cardStrength(b, trump) - E.cardStrength(a, trump));
  const chosen = await new Promise((resolve) => {
    clearEl(el);
    for (const card of sorted) {
      const cardEl = renderCard(card, {});
      cardEl.addEventListener("click", () => resolve(card), { once: true });
      el.appendChild(cardEl);
    }
  });
  hideOverlay("discard-overlay");
  return chosen;
}

async function showFarmersOverlay(hand) {
  showOverlay("farmers-overlay");
  const el = $("farmers-hand-cards");
  clearEl(el);
  const kept = new Set();
  const cardEls = hand.map((card) => {
    const cardEl = renderCard(card, {});
    cardEl.addEventListener("click", () => {
      const key = E.cardKey(card);
      if (kept.has(key)) {
        kept.delete(key);
        cardEl.classList.remove("kept");
      } else if (kept.size < 2) {
        kept.add(key);
        cardEl.classList.add("kept");
      }
      confirmBtn.disabled = kept.size !== 2;
      confirmBtn.style.opacity = kept.size === 2 ? "1" : "0.5";
    });
    el.appendChild(cardEl);
    return { card, cardEl };
  });
  const confirmBtn = $("farmers-confirm-btn");
  const skipBtn = $("farmers-skip-btn");
  confirmBtn.disabled = true;
  confirmBtn.style.opacity = "0.5";

  const result = await new Promise((resolve) => {
    const onConfirm = () => {
      if (kept.size !== 2) return;
      const keepCards = cardEls.filter(({ card }) => kept.has(E.cardKey(card))).map(({ card }) => card);
      resolve(keepCards);
    };
    const onSkip = () => resolve(null);
    confirmBtn.addEventListener("click", onConfirm, { once: true });
    skipBtn.addEventListener("click", onSkip, { once: true });
  });
  hideOverlay("farmers-overlay");
  return result;
}

// ===== Farmer's hand pass ===================================================

// Only one seat's hand ever gets checked and swapped: the hidden kitty only
// has 3 cards, so a second swap in the same deal would hand out duplicate
// cards. Two farmer's hands in one deal is rare enough that "first one found
// gets the offer" is an acceptable house-rule simplification.
async function offerFarmersHandSwaps() {
  if (!rules.farmersHand) return;
  for (let seat = 0; seat < 4; seat++) {
    if (!E.isFarmersHand(hands[seat])) continue;
    if (seat === 0) {
      showToast("Your hand is all 9s and 10s — farmer's hand swap available!", 2500);
      const keepCards = await showFarmersOverlay(hands[seat]);
      if (keepCards) {
        hands[seat] = E.swapFarmersHand(hands[seat], keepCards, hiddenKitty);
        showToast("Swapped in 3 fresh cards from the kitty.", 1600);
      }
    } else {
      // AI always takes the swap, keeping its two strongest cards (no trump yet, so raw rank).
      const sortedByRank = hands[seat].slice().sort((a, b) => E.RANK_ORDER[b[0]] - E.RANK_ORDER[a[0]]);
      const keepCards = sortedByRank.slice(0, 2);
      hands[seat] = E.swapFarmersHand(hands[seat], keepCards, hiddenKitty);
    }
    return;
  }
}

// ===== Bidding =============================================================

async function getHumanBidRound1(hand, turnedSuit) {
  const recommended = E.recommendBidAction(hand, { roundNum: 1, isDealer: false, turnedSuit });
  const actual = await showBid1Modal(upCard);
  decisionsLog.push([actual, recommended]);
  return actual;
}

async function getAiBidRound1(hand, turnedSuit) {
  await sleep(650 + Math.random() * 400);
  let action = aiFns().bid(hand, { roundNum: 1, turnedSuit });
  if (action === "order_up_alone" && !rules.allowGoingAlone) action = "order_up";
  return action;
}

async function runRound1Bidding(turnedSuit) {
  for (let offset = 1; offset <= 4; offset++) {
    const seat = (dealerSeat + offset) % 4;
    const action = seat === 0 ? await getHumanBidRound1(hands[seat], turnedSuit) : await getAiBidRound1(hands[seat], turnedSuit);
    if (action === "pass") {
      showToast(`${SEAT_NAMES[seat]} passes.`);
      continue;
    }
    return { seat, alone: action === "order_up_alone" };
  }
  return null;
}

async function getHumanBidRound2(hand, availableSuits, mustCall) {
  const recommended = E.recommendBidAction(hand, { roundNum: 2, isDealer: mustCall, availableSuits });
  const actual = await showBid2Modal(availableSuits, mustCall);
  const normalizedActual = actual === "pass" ? "pass" : `${actual.suit}:${actual.alone}`;
  const normalizedRec = recommended === "pass" ? "pass" : `${recommended.suit}:${recommended.alone}`;
  decisionsLog.push([normalizedActual, normalizedRec]);
  return actual;
}

async function getAiBidRound2(hand, availableSuits, mustCall) {
  await sleep(650 + Math.random() * 400);
  let action = aiFns().bid(hand, { roundNum: 2, availableSuits, isDealer: mustCall });
  if (action !== "pass" && action.alone && !rules.allowGoingAlone) action = { ...action, alone: false };
  return action;
}

async function runRound2Bidding(turnedSuit) {
  const availableSuits = E.SUITS.filter((s) => s !== turnedSuit);
  for (let offset = 1; offset <= 4; offset++) {
    const seat = (dealerSeat + offset) % 4;
    const mustCall = rules.stickTheDealer && seat === dealerSeat;
    const action = seat === 0
      ? await getHumanBidRound2(hands[seat], availableSuits, mustCall)
      : await getAiBidRound2(hands[seat], availableSuits, mustCall);
    if (action === "pass") {
      showToast(`${SEAT_NAMES[seat]} passes.`);
      continue;
    }
    return { seat, suit: action.suit, alone: action.alone };
  }
  return null;
}

// ===== Trick play ===========================================================

function removeCardFromHand(seat, card) {
  hands[seat] = E.discard(hands[seat], card);
}

function renderPlayedCard(seat, card) {
  const slot = TRICK_SLOT[seat];
  clearEl(slot);
  const el = renderCard(card, { className: "dealt-in" });
  slot.appendChild(el);
  if (seat === 0) renderBottomHandStatic(hands[0]);
  else renderOpponentHand(seat, hands[seat].length);
}

async function sweepTrick(winnerSeat) {
  await sleep(650);
  for (let s = 0; s < 4; s++) {
    TRICK_SLOT[s].classList.add(`sweep-${winnerSeat}`);
  }
  await sleep(430);
  for (let s = 0; s < 4; s++) {
    clearEl(TRICK_SLOT[s]);
    TRICK_SLOT[s].classList.remove(`sweep-${winnerSeat}`);
  }
}

async function playTrick(leaderSeat, trump) {
  let ledSuit = null;
  const plays = [];
  let seat = leaderSeat;
  for (let i = 0; i < 4; i++) {
    if (seat === sittingOutSeat) {
      seat = (seat + 1) % 4;
      continue;
    }
    let card;
    if (seat === 0) {
      const legal = E.legalPlays(hands[0], ledSuit, trump);
      showToast("Your turn — pick a card.", 0);
      card = await chooseCardFromHand(hands[0], (c) => legal.some((l) => E.cardsEqual(l, c)));
      hideToast();
    } else {
      showToast(`${SEAT_NAMES[seat]} is thinking...`, 0);
      await sleep(550 + Math.random() * 500);
      card = aiFns().card(hands[seat], plays.map((p) => p.card), trump, ledSuit);
      hideToast();
    }
    removeCardFromHand(seat, card);
    if (ledSuit === null) ledSuit = E.effectiveSuit(card, trump);
    plays.push({ seat, card });
    renderPlayedCard(seat, card);
    seat = (seat + 1) % 4;
  }
  const winnerSeat = E.determineTrickWinner(plays, trump);
  showToast(`${SEAT_NAMES[winnerSeat]} takes the trick.`, 1200);
  await sweepTrick(winnerSeat);
  return winnerSeat;
}

// ===== Full hand ============================================================

async function playHand() {
  const turnedSuit = upCard[1];
  let trump = turnedSuit;
  let makerSeat, alone;

  let result = await runRound1Bidding(turnedSuit);
  if (result) {
    ({ seat: makerSeat, alone } = result);
    showToast(`${SEAT_NAMES[makerSeat]} orders it up${alone ? " and goes alone" : ""}!`, 2000);
    hands[dealerSeat] = E.pickUpCard(hands[dealerSeat], upCard);
    renderHandsAll();
    if (dealerSeat === 0) {
      const chosen = await showDiscardOverlay(hands[0], trump);
      hands[0] = E.discard(hands[0], chosen);
    } else {
      await sleep(500);
      const chosen = aiFns().discard(hands[dealerSeat], trump);
      hands[dealerSeat] = E.discard(hands[dealerSeat], chosen);
    }
  } else {
    result = await runRound2Bidding(turnedSuit);
    if (!result) return null; // redeal
    ({ seat: makerSeat, suit: trump, alone } = result);
    showToast(`${SEAT_NAMES[makerSeat]} calls ${trump}${alone ? " and goes alone" : ""}!`, 2000);
  }

  const makingTeam = E.TEAM_OF_SEAT[makerSeat];
  sittingOutSeat = alone ? (makerSeat + 2) % 4 : null;
  renderHandsAll();
  updateTrumpBanner(trump, makerSeat);

  const tricksByTeam = { 0: 0, 1: 0 };
  let leaderSeat = (dealerSeat + 1) % 4;
  if (leaderSeat === sittingOutSeat) leaderSeat = (leaderSeat + 1) % 4;

  for (let t = 0; t < 5; t++) {
    const winnerSeat = await playTrick(leaderSeat, trump);
    tricksByTeam[E.TEAM_OF_SEAT[winnerSeat]] += 1;
    updateTrickPills(tricksByTeam);
    leaderSeat = winnerSeat;
  }

  sittingOutSeat = null;
  return { points: E.scoreHand(tricksByTeam, makingTeam, alone), makingTeam, alone, tricksByTeam };
}

function updateTrickPills(tricksByTeam) {
  for (let seat = 0; seat < 4; seat++) {
    TRICKS_PILL[seat].textContent = tricksByTeam[E.TEAM_OF_SEAT[seat]];
  }
}

function updateTrumpBanner(trump, makerSeat) {
  const banner = $("trump-banner");
  banner.classList.remove("hidden");
  const suitEl = $("trump-suit-display");
  suitEl.textContent = `${E.SUIT_SYMBOL[trump]} ${trump}`;
  suitEl.className = `trump-suit ${trumpSuitClass(trump)}`;
  $("maker-label").textContent = `${SEAT_NAMES[makerSeat]} called it`;
}

function renderHandsAll() {
  renderBottomHandStatic(hands[0]);
  renderOpponentHand(1, hands[1].length);
  renderOpponentHand(2, hands[2].length);
  renderOpponentHand(3, hands[3].length);
}

// ===== Full game ============================================================

async function dealNewHand() {
  const deck = E.shuffle(E.createDeck());
  const dealt = E.dealHands(deck);
  hands = dealt.hands;
  hiddenKitty = dealt.hiddenKitty;
  upCard = dealt.upCard;

  for (let seat = 0; seat < 4; seat++) TRICKS_PILL[seat].textContent = 0;
  $("trump-banner").classList.add("hidden");
  renderHandsAll();
  clearEl($("upcard-holder"));
  $("upcard-holder").appendChild(renderCard(upCard, { className: "dealt-in" }));
  updateDealerChip();
  await offerFarmersHandSwaps();
  renderHandsAll();
}

function showHandResult({ points, makingTeam, alone, tricksByTeam }) {
  scores[0] += points[0] || 0;
  scores[1] += points[1] || 0;
  updateScoreboard();

  const madeIt = points[makingTeam] > 0;
  const teamLabel = makingTeam === 0 ? "You and North" : "East and West";
  let headline, detail;
  if (!madeIt) {
    headline = "Euchred!";
    detail = `${teamLabel} were set. The defenders score 2 points.`;
  } else if (points[makingTeam] === 4) {
    headline = "Lone March!";
    detail = `${teamLabel} swept all 5 tricks alone for 4 points.`;
  } else if (points[makingTeam] === 2) {
    headline = "March!";
    detail = `${teamLabel} took all 5 tricks for 2 points.`;
  } else {
    headline = "Hand Won";
    detail = `${teamLabel} made their bid for 1 point.`;
  }
  $("result-headline").textContent = headline;
  $("result-detail").textContent = detail;
  $("result-score-us").textContent = scores[0];
  $("result-score-them").textContent = scores[1];
  showOverlay("hand-result-overlay");
  return waitOnce($("next-hand-btn"));
}

function finishGame() {
  const won = scores[0] >= 10;
  $("game-over-headline").textContent = won ? "Victory! You reached 10." : "Defeat. They reached 10.";
  $("game-over-eyebrow").textContent = won ? "You Win" : "Game Over";

  const qualityRate = AI.computeQualityRate(decisionsLog);
  const before = mmrData.mmr;
  mmrData.mmr = AI.updateMmr(mmrData.mmr, qualityRate);
  mmrData.gamesPlayed += 1;
  AI.saveMmr(mmrData);

  const change = mmrData.mmr - before;
  $("mmr-change").textContent = `${change >= 0 ? "+" : ""}${change}`;
  $("quality-rate").textContent = `${Math.round(qualityRate * 100)}%`;
  updateDifficultyChip();
  showOverlay("game-over-overlay");
  return waitOnce($("rematch-btn"));
}

async function runGame() {
  scores = { 0: 0, 1: 0 };
  decisionsLog = [];
  dealerSeat = 0;
  updateScoreboard();

  while (scores[0] < 10 && scores[1] < 10) {
    await dealNewHand();
    const result = await playHand();
    if (result) {
      await showHandResult(result);
      hideOverlay("hand-result-overlay");
    } else {
      showToast("Everyone passed — redealing.", 1800);
      await sleep(1200);
    }
    dealerSeat = (dealerSeat + 1) % 4;
  }
  await finishGame();
  hideOverlay("game-over-overlay");
  runGame();
}

// ===== Settings & start screen wiring =======================================

function applyRuleSwitches() {
  $("rule-alone").checked = rules.allowGoingAlone;
  $("rule-stick").checked = rules.stickTheDealer;
  $("rule-farmers").checked = rules.farmersHand;
  document.querySelectorAll(".btn-choice").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.difficulty === difficultyOverride);
  });
}

function wireSettings() {
  $("rule-alone").addEventListener("change", (e) => { rules.allowGoingAlone = e.target.checked; });
  $("rule-stick").addEventListener("change", (e) => { rules.stickTheDealer = e.target.checked; });
  $("rule-farmers").addEventListener("change", (e) => { rules.farmersHand = e.target.checked; });
  document.querySelectorAll(".btn-choice").forEach((btn) => {
    btn.addEventListener("click", () => {
      difficultyOverride = btn.dataset.difficulty;
      applyRuleSwitches();
      updateDifficultyChip();
    });
  });
  $("settings-btn").addEventListener("click", () => { applyRuleSwitches(); showOverlay("settings-overlay"); });
  $("start-settings-btn").addEventListener("click", () => { applyRuleSwitches(); showOverlay("settings-overlay"); });
  $("settings-close-btn").addEventListener("click", () => hideOverlay("settings-overlay"));
  $("rules-btn").addEventListener("click", () => showOverlay("rules-overlay"));
  $("rules-close-btn").addEventListener("click", () => hideOverlay("rules-overlay"));
}

function updateStartStats() {
  $("start-mmr").textContent = mmrData.mmr;
  $("start-difficulty").textContent = AI.difficultyTier(mmrData.mmr)[0].toUpperCase() + AI.difficultyTier(mmrData.mmr).slice(1);
  $("start-games").textContent = mmrData.gamesPlayed;
}

function init() {
  updateStartStats();
  updateDifficultyChip();
  wireSettings();
  window.addEventListener("resize", () => { try { updateDealerChip(); } catch {} });

  $("new-game-btn").addEventListener("click", () => {
    hideOverlay("start-overlay");
    runGame();
  });
  $("rematch-btn").addEventListener("click", () => {
    updateStartStats();
  });
}

init();
