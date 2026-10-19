/**
 * CidTimerStop frontend extension.
 *
 * Draws a retro digital alarm clock on the node (seven-segment red LED with
 * ghost segments, glow and scanlines) and drives its states:
 *
 *   READY  before the first run - ghost "88:88.8", like a clock that is off
 *   RUN    while the queue executes - counts up live, colon blinks
 *   DONE   frozen result when CidTimerStop executes (authoritative value)
 *   PAUSED queue emptied without this node executing - frozen count-up
 *
 * The panel is rendered into a small offscreen canvas (2x for crispness) and
 * cached, so live counting costs one blit per repaint.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const CLOCK_H = 100;
const IDLE_TEXT = "88:88.8";

const COLORS = {
  lit: "#ff4034",
  core: "#ffb09e",
  unlit: "#2e0f10",
  ghost: "#5f1c1e",
  displayBg: "#160b0b",
  displayEdge: "#080505",
  bezel: "#17171d",
  bezelEdge: "#3c3c48",
  label: "#8c4e4e",
  unit: "#703e3e",
  statusReady: "#6e4040",
  statusRun: "#ff6054",
  statusDone: "#80dc94",
  runDot: "#ff6054",
};

const STATUS_COLOR = {
  READY: COLORS.statusReady,
  RUN: COLORS.statusRun,
  DONE: COLORS.statusDone,
  PAUSED: COLORS.statusReady,
};

const SEGMENTS = {
  0: "abcdef",
  1: "bc",
  2: "abged",
  3: "abgcd",
  4: "fgbc",
  5: "afgcd",
  6: "afgedc",
  7: "abc",
  8: "abcdefg",
  9: "abcdfg",
};

// ---------------------------------------------------------------------------
// Geometry helpers (fractions of the panel height, matching the approved mockup)
// ---------------------------------------------------------------------------

const segH = (x1, x2, yc, t) => [
  [x1, yc],
  [x1 + t / 2, yc - t / 2],
  [x2 - t / 2, yc - t / 2],
  [x2, yc],
  [x2 - t / 2, yc + t / 2],
  [x1 + t / 2, yc + t / 2],
];

const segV = (y1, y2, xc, t) => [
  [xc, y1],
  [xc + t / 2, y1 + t / 2],
  [xc + t / 2, y2 - t / 2],
  [xc, y2],
  [xc - t / 2, y2 - t / 2],
  [xc - t / 2, y1 + t / 2],
];

function digitPolys(x, y, w, h) {
  const t = w * 0.2;
  const g = t * 0.3;
  return {
    a: segH(x + g, x + w - g, y, t),
    g: segH(x + g, x + w - g, y + h / 2, t),
    d: segH(x + g, x + w - g, y + h, t),
    f: segV(y + g, y + h / 2 - g, x, t),
    b: segV(y + g, y + h / 2 - g, x + w, t),
    e: segV(y + h / 2 + g, y + h - g, x, t),
    c: segV(y + h / 2 + g, y + h - g, x + w, t),
  };
}

function shrinkPoly(pts, f) {
  let cx = 0;
  let cy = 0;
  for (const [x, y] of pts) {
    cx += x;
    cy += y;
  }
  cx /= pts.length;
  cy /= pts.length;
  return pts.map(([x, y]) => [cx + (x - cx) * f, cy + (y - cy) * f]);
}

function fillPoly(ctx, pts) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fill();
}

const isDigit = (c) => c >= "0" && c <= "9";
const pad2 = (n) => String(n).padStart(2, "0");

// ---------------------------------------------------------------------------
// Clock value -> display text + unit label groups
// ---------------------------------------------------------------------------

function clockDigits(seconds) {
  const s = Math.max(0, seconds);
  if (s < 3600) {
    const m = Math.floor(s / 60);
    const rest = s - m * 60;
    const si = Math.floor(rest);
    const tenth = Math.floor((rest - si) * 10);
    return {
      text: `${pad2(m)}:${pad2(si)}.${tenth}`,
      groups: [
        [0, 1],
        [2, 3],
      ],
      labels: ["MIN", "SEC"],
    };
  }
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s - hh * 3600) / 60);
  const ss = Math.floor(s - hh * 3600 - mm * 60);
  return {
    text: `${hh}:${pad2(mm)}:${pad2(ss)}`,
    groups: [
      [0],
      [1, 2],
      [3, 4],
    ],
    labels: ["HRS", "MIN", "SEC"],
  };
}

// ---------------------------------------------------------------------------
// Panel renderer (offscreen, cached)
// ---------------------------------------------------------------------------

const panelCache = new Map();
const CACHE_MAX = 64;

function renderClockPanel(spec) {
  const key = JSON.stringify(spec);
  if (panelCache.has(key)) return panelCache.get(key);

  const { w, h, text, name, status, ghost, blink, groups, labels } = spec;
  const dpr = 2;
  const cv = document.createElement("canvas");
  cv.width = Math.max(1, Math.ceil(w * dpr));
  cv.height = Math.max(1, Math.ceil(h * dpr));
  const ctx = cv.getContext("2d");
  ctx.scale(dpr, dpr);

  // Housing / bezel
  const bezelR = h * 0.057;
  ctx.fillStyle = COLORS.bezel;
  ctx.strokeStyle = COLORS.bezelEdge;
  ctx.lineWidth = Math.max(1, h * 0.0052);
  ctx.beginPath();
  ctx.roundRect(0.5, 0.5, w - 1, h - 1, bezelR);
  ctx.fill();
  ctx.stroke();

  // Recessed display
  const m = h * 0.0476;
  const dx0 = m;
  const dy0 = m;
  const dx1 = w - m;
  const dy1 = h - m;
  ctx.fillStyle = COLORS.displayBg;
  ctx.strokeStyle = COLORS.displayEdge;
  ctx.lineWidth = Math.max(1, h * 0.0048);
  ctx.beginPath();
  ctx.roundRect(dx0, dy0, dx1 - dx0, dy1 - dy0, h * 0.038);
  ctx.fill();
  ctx.stroke();

  // ---- Digit layout: fit both width and height ----
  const y0 = dy0 + h * 0.124;
  const y1 = dy1 - h * 0.095;
  const dhMax = y1 - y0;
  const avail = dx1 - dx0 - h * 0.0667;
  const chars = [...text];
  const nDig = chars.filter(isDigit).length;
  const nColon = chars.filter((c) => c === ":").length;
  const nDot = chars.filter((c) => c === ".").length;
  const nGap = Math.max(chars.length - 1, 0);
  const units = nDig + 0.62 * nColon + 0.45 * nDot + 0.34 * nGap;
  const dw = Math.min(dhMax * 0.56, avail / units);
  const dh = dw / 0.56;
  const yTop = y0 + (dhMax - dh) / 2;
  const cw = 0.62 * dw;
  const dotw = 0.45 * dw;
  const gap = 0.34 * dw;
  const charW = (c) => (isDigit(c) ? dw : c === ":" ? cw : dotw);

  let total = 0;
  for (const c of chars) total += charW(c);
  total += gap * nGap;

  let x = (dx0 + dx1 - total) / 2;
  const digitX = [];
  const glowBlur = Math.max(2.5, h * 0.0167);

  const drawSegment = (pts, color, glow) => {
    ctx.save();
    if (glow) {
      ctx.shadowColor = COLORS.lit;
      ctx.shadowBlur = glowBlur;
    }
    ctx.fillStyle = color;
    fillPoly(ctx, pts);
    ctx.restore();
  };

  for (const c of chars) {
    if (isDigit(c)) {
      const polys = digitPolys(x, yTop, dw, dh);
      const on = SEGMENTS[c] || "";
      digitX.push(x);
      for (const s of "abcdefg") {
        const lit = !ghost && on.includes(s);
        drawSegment(polys[s], ghost ? COLORS.ghost : lit ? COLORS.lit : COLORS.unlit, lit);
      }
    } else if (c === ":") {
      const sq = 0.26 * dw;
      const ccx = x + cw / 2;
      const lit = !ghost && blink;
      for (const fy of [0.3, 0.7]) {
        const cyc = yTop + dh * fy;
        const pts = [
          [ccx - sq / 2, cyc - sq / 2],
          [ccx + sq / 2, cyc - sq / 2],
          [ccx + sq / 2, cyc + sq / 2],
          [ccx - sq / 2, cyc + sq / 2],
        ];
        drawSegment(pts, lit ? COLORS.lit : ghost ? COLORS.ghost : COLORS.unlit, lit);
      }
    } else if (c === ".") {
      const sq = 0.15 * dw;
      const bx = x + dotw / 2;
      const by = yTop + dh - sq / 2 - 1;
      const pts = [
        [bx - sq / 2, by - sq / 2],
        [bx + sq / 2, by - sq / 2],
        [bx + sq / 2, by + sq / 2],
        [bx - sq / 2, by + sq / 2],
      ];
      drawSegment(pts, ghost ? COLORS.ghost : COLORS.lit, !ghost);
    }
    x += charW(c) + gap;
  }

  // Hot cores inside lit segments
  if (!ghost) {
    ctx.fillStyle = COLORS.core;
    x = (dx0 + dx1 - total) / 2;
    for (const c of chars) {
      if (isDigit(c)) {
        const polys = digitPolys(x, yTop, dw, dh);
        for (const s of SEGMENTS[c] || "") fillPoly(ctx, shrinkPoly(polys[s], 0.52));
      }
      x += charW(c) + gap;
    }
  }

  // Scanlines over the display glass
  ctx.globalAlpha = 0.13;
  ctx.fillStyle = "#000";
  const scanStep = Math.max(2, h * 0.019);
  for (let sy = dy0 + 2; sy < dy1 - 1; sy += scanStep) {
    ctx.fillRect(dx0 + 1, sy, dx1 - dx0 - 2, Math.max(0.5, h * 0.0038));
  }
  ctx.globalAlpha = 1;

  // Header row: timer name (brand label) + status
  const nameSize = Math.max(8, h * 0.0405);
  const statusSize = Math.max(7, h * 0.0357);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = COLORS.label;
  ctx.font = `bold ${nameSize}px ui-monospace, Menlo, Consolas, monospace`;
  const shown = name.length > 14 ? name.slice(0, 13) + "\u2026" : name;
  ctx.fillText(shown.toUpperCase(), (dx0 + dx1) / 2, dy0 + h * 0.0524);

  ctx.textAlign = "right";
  ctx.fillStyle = STATUS_COLOR[status] || COLORS.statusReady;
  ctx.font = `bold ${statusSize}px ui-monospace, Menlo, Consolas, monospace`;
  ctx.fillText(status, dx1 - h * 0.038, dy0 + h * 0.0524);
  if (status === "RUN") {
    ctx.fillStyle = COLORS.runDot;
    ctx.beginPath();
    ctx.arc(dx1 - h * 0.286, dy0 + h * 0.0524, h * 0.0119, 0, Math.PI * 2);
    ctx.fill();
  }

  // Unit labels under the digit groups
  const unitSize = Math.max(6.5, h * 0.0333);
  ctx.font = `bold ${unitSize}px ui-monospace, Menlo, Consolas, monospace`;
  ctx.textAlign = "center";
  ctx.fillStyle = COLORS.unit;
  groups.forEach((group, i) => {
    const centers = group.map((d) => digitX[d] + dw / 2);
    const center = (Math.min(...centers) + Math.max(...centers)) / 2;
    ctx.fillText(labels[i], center, dy1 - h * 0.0429);
  });

  if (panelCache.size >= CACHE_MAX) panelCache.clear();
  panelCache.set(key, cv);
  return cv;
}

// ---------------------------------------------------------------------------
// Live state, driven by execution events
// ---------------------------------------------------------------------------

function ensureState(node) {
  if (!node.cidTimer) node.cidTimer = { state: "ready", elapsed: null, t0: 0 };
  return node.cidTimer;
}

function timerNameOf(node) {
  const w = node.widgets?.find((widget) => widget.name === "timer_name");
  const value = (w?.value ?? "default").toString().trim();
  return value || "default";
}

const runningStops = new Set();
let ticker = null;

function ensureTicker() {
  if (ticker) return;
  ticker = setInterval(() => {
    for (const node of runningStops) node.setDirtyCanvas?.(true, true);
  }, 100);
}

function stopTickerIfIdle() {
  if (ticker && runningStops.size === 0) {
    clearInterval(ticker);
    ticker = null;
  }
}

function markRunning(name) {
  for (const node of app.graph?.nodes ?? []) {
    if ((node.comfyClass ?? node.type) !== "CidTimerStop") continue;
    if (timerNameOf(node) !== name) continue;
    const st = ensureState(node);
    st.state = "running";
    st.t0 = performance.now();
    runningStops.add(node);
    ensureTicker();
    node.setDirtyCanvas?.(true, true);
  }
}

function freezePaused() {
  for (const node of [...runningStops]) {
    const st = ensureState(node);
    st.elapsed = (performance.now() - st.t0) / 1000;
    st.state = "paused";
    node.setDirtyCanvas?.(true, true);
  }
  runningStops.clear();
  stopTickerIfIdle();
}

function drawWidgetClock(ctx, node, width, posY) {
  const st = ensureState(node);
  const inset = 10;
  const w = Math.max(140, width - inset * 2);
  const name = timerNameOf(node);

  let spec;
  if (st.state === "running") {
    const now = performance.now();
    spec = { ...clockDigits((now - st.t0) / 1000), status: "RUN", blink: Math.floor(now / 500) % 2 === 0 };
  } else if (st.state === "done" || st.state === "paused") {
    spec = { ...clockDigits(st.elapsed ?? 0), status: st.state === "done" ? "DONE" : "PAUSED", blink: true };
  } else {
    spec = {
      text: IDLE_TEXT,
      groups: [
        [0, 1],
        [2, 3],
      ],
      labels: ["MIN", "SEC"],
      status: "READY",
      ghost: true,
      blink: true,
    };
  }

  const panel = renderClockPanel({ w, h: CLOCK_H, name, ...spec });
  ctx.drawImage(panel, inset, posY + 2, w, CLOCK_H);
}

// ---------------------------------------------------------------------------
// Extension registration
// ---------------------------------------------------------------------------

app.registerExtension({
  name: "CidTimerStopExtension",
  setup() {
    api.addEventListener("executed", ({ detail }) => {
      const started = detail?.output?.timer_started;
      if (Array.isArray(started) && started.length > 0) markRunning(String(started[0]));
    });
    api.addEventListener("status", ({ detail }) => {
      const remaining = detail?.exec_info?.queue_remaining;
      if (typeof remaining === "number" && remaining === 0) freezePaused();
    });
  },
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "CidTimerStop") return;

    // Reflect the connected input type onto the pass-through output
    const origOnConnChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
      origOnConnChange?.call(this, type, index, connected, link_info);
      if (type !== 1) return;
      const input = this.inputs?.[index];
      if (!input || input.name !== "input") return;
      let newType = "*";
      if (connected && link_info) {
        const originNode = app.graph.getNodeById(link_info.origin_id);
        const out = originNode?.outputs?.[link_info.origin_slot];
        if (out?.type && out.type !== "*") newType = out.type;
      }
      const output = this.outputs?.[0];
      if (output) {
        output.type = newType;
        output.label = newType;
        output.name = newType;
      }
    };

    const origOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      origOnNodeCreated?.call(this);
      const node = this;
      ensureState(node);

      const widget = {
        type: "cid_timer_clock",
        name: "clock",
        value: "",
        y: 0,
        serialize: false,
        tooltip: "Elapsed time between the paired CidTimerStart and this node",
        computeSize(width) {
          return [width, CLOCK_H];
        },
        draw(ctx, n, width, posY) {
          drawWidgetClock(ctx, n, width, posY);
        },
        mouse() {
          return false;
        },
      };
      if (node.addCustomWidget) node.addCustomWidget(widget);
      else node.widgets.push(widget);
      node.expandToFitContent?.();

      // Freeze the clock with the authoritative backend value
      node.onExecuted = function (output) {
        const st = ensureState(this);
        let elapsed = Array.isArray(output?.elapsed) ? Number(output.elapsed[0]) : NaN;
        if (!Number.isFinite(elapsed)) {
          elapsed = st.state === "running" ? (performance.now() - st.t0) / 1000 : st.elapsed ?? 0;
        }
        st.state = "done";
        st.elapsed = elapsed;
        runningStops.delete(this);
        stopTickerIfIdle();
        this.setDirtyCanvas?.(true, true);
      };
    };
  },
});
