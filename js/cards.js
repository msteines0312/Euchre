// Procedural SVG card faces/backs. Drawn in code (no image assets) so the
// deck is crisp at any size and free of licensing concerns.

import { SUIT_SYMBOL, SUIT_COLOR } from "./engine.js";

const SUIT_PATHS = {
  Spades: "M12 2 C7 7 2 11 2 15.5 A5 5 0 0 0 10.8 18.8 C10.2 20.6 9 21.6 6.5 22.5 L17.5 22.5 C15 21.6 13.8 20.6 13.2 18.8 A5 5 0 0 0 22 15.5 C22 11 17 7 12 2 Z",
  Hearts: "M12 21 C5 15.5 2 12 2 8.2 A4.8 4.8 0 0 1 12 6.6 A4.8 4.8 0 0 1 22 8.2 C22 12 19 15.5 12 21 Z",
  Diamonds: "M12 2 L20 13 L12 23 L4 13 Z",
  Clubs: "M12 3 A4 4 0 0 1 15.2 9.6 A4 4 0 1 1 13.6 17 C13.9 19 14.8 20.5 17.5 22.5 L6.5 22.5 C9.2 20.5 10.1 19 10.4 17 A4 4 0 1 1 8.8 9.6 A4 4 0 0 1 12 3 Z",
};

function svgEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

function suitGlyph(suit, size, x, y) {
  const g = svgEl("g", { transform: `translate(${x - size / 2}, ${y - size / 2}) scale(${size / 24})` });
  const path = svgEl("path", { d: SUIT_PATHS[suit], class: `suit-fill suit-${SUIT_COLOR[suit]}` });
  g.appendChild(path);
  return g;
}

// Builds a full <svg> card face, `rank`/`suit` e.g. "J","Spades".
function buildCardFaceSvg(rank, suit) {
  const svg = svgEl("svg", { viewBox: "0 0 100 140", class: "card-face-svg" });
  svg.appendChild(svgEl("rect", { x: 1.5, y: 1.5, width: 97, height: 137, rx: 9, class: "card-bg" }));
  svg.appendChild(svgEl("rect", { x: 1.5, y: 1.5, width: 97, height: 137, rx: 9, class: "card-border" }));

  const colorClass = `suit-${SUIT_COLOR[suit]}`;

  const cornerTop = svgEl("g", { class: `card-corner ${colorClass}` });
  const rankTop = svgEl("text", { x: 10, y: 22, class: "card-rank" });
  rankTop.textContent = rank;
  cornerTop.appendChild(rankTop);
  cornerTop.appendChild(suitGlyph(suit, 14, 16, 34));
  svg.appendChild(cornerTop);

  const cornerBottom = svgEl("g", {
    class: `card-corner ${colorClass}`,
    transform: "rotate(180 50 70)",
  });
  const rankBottom = svgEl("text", { x: 10, y: 22, class: "card-rank" });
  rankBottom.textContent = rank;
  cornerBottom.appendChild(rankBottom);
  cornerBottom.appendChild(suitGlyph(suit, 14, 16, 34));
  svg.appendChild(cornerBottom);

  svg.appendChild(suitGlyph(suit, 42, 50, 70));

  return svg;
}

function buildCardBackSvg() {
  const svg = svgEl("svg", { viewBox: "0 0 100 140", class: "card-back-svg" });
  svg.appendChild(svgEl("rect", { x: 1.5, y: 1.5, width: 97, height: 137, rx: 9, class: "card-back-bg" }));
  svg.appendChild(svgEl("rect", { x: 8, y: 8, width: 84, height: 124, rx: 6, class: "card-back-inset" }));
  const g = svgEl("g", { class: "card-back-emblem" });
  g.appendChild(suitGlyph("Spades", 30, 50, 70));
  svg.appendChild(g);
  return svg;
}

// Returns a DOM element (.card) representing a playing card. `faceUp=false`
// renders the back. `card` is [rank, suit].
function renderCard(card, { faceUp = true, className = "" } = {}) {
  const el = document.createElement("div");
  el.className = `card ${className}`.trim();
  if (faceUp) {
    const [rank, suit] = card;
    el.appendChild(buildCardFaceSvg(rank, suit));
    el.dataset.rank = rank;
    el.dataset.suit = suit;
  } else {
    el.appendChild(buildCardBackSvg());
    el.classList.add("card-back");
  }
  return el;
}

export { renderCard, buildCardFaceSvg, buildCardBackSvg, SUIT_SYMBOL };
