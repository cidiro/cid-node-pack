import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { Tournament } from './cid_image_ab_testing_engine.mjs';

// Canvas overlay/contain sizing follows rgthree's Image Comparer.
// Copyright (c) 2023 Regis Gaughan, III (rgthree). See THIRD_PARTY_NOTICES.md.
export function mountTournament(node) {
  const root = document.createElement('div');
  root.style.cssText = 'display:flex;flex-direction:column;gap:8px;padding:10px;box-sizing:border-box;background:#181b22;color:#eee;font:13px sans-serif;height:100%;overflow:auto;';
  const status = document.createElement('div');
  status.style.whiteSpace = 'pre-wrap';
  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'width:100%;height:260px;flex-shrink:0;background:#101116;touch-action:none;';
  const controls = document.createElement('div'); controls.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;';
  const details = document.createElement('details');
  const summary = document.createElement('summary'); summary.textContent = 'Results and audit history';
  const history = document.createElement('pre'); history.style.cssText = 'white-space:pre-wrap;font:11px monospace;';
  details.append(summary, history);
  const finalists = document.createElement('div'); finalists.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;';
  root.append(status, canvas, controls, finalists, details);
  let engine, mode = 'Slide', split = .5, down = false, over = false, disposed = false;
  const loaded = new Map();
  function button(label, callback) {
    const b = document.createElement('button'); b.textContent = label;
    b.onclick = () => { callback(); render(); }; controls.append(b); return b;
  }
  let voteLocked = false;
  function vote(side) {
    if (voteLocked || !engine?.current) return;
    voteLocked = true; engine.vote(engine.current[side]);
    setTimeout(() => { voteLocked = false; render(); }, 300);
  }
  const chooseA = button('Choose A', () => vote(0));
  const chooseB = button('Choose B', () => vote(1));
  const undo = button('Undo Last Vote', () => engine?.undo());
  const end = button('End Session', () => engine?.end());
  const resume = button('Continue', () => engine?.resume());
  button('Retry previews', () => { loaded.clear(); });
  button('Slide / Click', () => { mode = mode === 'Slide' ? 'Click' : 'Slide'; });
  function image(index) {
    if (!engine || index === undefined) return null;
    const candidate = engine.s.images[index];
    const p = candidate.preview;
    const url = api.apiURL(`/view?${new URLSearchParams(p)}`);
    if (!loaded.has(url)) {
      const entry = {img: new Image(), ready: false, failed: false};
      loaded.set(url, entry);
      entry.img.onload = () => { entry.ready = true; if (!disposed) render(); };
      entry.img.onerror = () => { entry.failed = true; if (!disposed) render(); };
      entry.img.src = url;
    }
    return loaded.get(url);
  }
  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(1, canvas.clientWidth), height = 260;
    canvas.width = width * dpr; canvas.height = height * dpr;
    const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
    const pair = engine?.current;
    const winner = engine?.s.result?.winner;
    const indices = winner !== undefined ? [winner] : pair || [];
    function paint(index, clip = null) {
      const entry = image(index); if (!entry?.ready) return;
      const img = entry.img, scale = Math.min(width / img.naturalWidth, height / img.naturalHeight);
      const w = img.naturalWidth * scale, h = img.naturalHeight * scale;
      ctx.save();
      if (clip !== null) { ctx.beginPath(); ctx.rect(0, 0, clip, height); ctx.clip(); }
      ctx.drawImage(img, (width-w)/2, (height-h)/2, w, h); ctx.restore();
    }
    if (indices.length === 1) paint(indices[0]);
    else if (indices.length === 2) {
      if (mode === 'Click') paint(indices[down ? 1 : 0]);
      else { paint(indices[0]); if (over) { paint(indices[1], split * width); ctx.strokeStyle = 'white'; ctx.beginPath(); ctx.moveTo(split*width, 0); ctx.lineTo(split*width, height); ctx.stroke(); } }
      ctx.fillStyle = '#000b'; ctx.fillRect(0, 0, width, 22);
      ctx.fillStyle = 'white'; ctx.font = '12px sans-serif';
      ctx.fillText(mode === 'Slide' ? 'B ← divider → A · hover to compare' : 'A · hold to view B', 8, 15);
    }
  }
  function render() {
    if (disposed) return;
    if (!engine) { status.textContent = 'Run the workflow to load candidates.'; chooseA.disabled = chooseB.disabled = undo.disabled = end.disabled = resume.disabled = true; draw(); return; }
    engine.refresh();
    const s = engine.s;
    node.properties.cid_ab_session = s;
    const pair = engine.current;
    const entries = (pair || (s.result ? [s.result.winner] : [])).map(image);
    const ready = entries.length === 2 && entries.every(e => e.ready);
    const missing = entries.some(e => e.failed);
    chooseA.disabled = chooseB.disabled = voteLocked || !pair || !ready || s.used >= s.budget || s.budget < s.required;
    undo.disabled = !engine.votes.length;
    end.disabled = !!s.result || s.phase === 'selection';
    resume.disabled = s.used >= s.budget || (!s.result && s.phase !== 'selection') || ['confirmed', 'single'].includes(s.result?.method);
    status.textContent = `${s.result?.label || (s.phase === 'selection' ? 'Choose a finalist below' : s.phase.replaceAll('_', ' '))}\nInitial pairs ${s.coverage}/${s.required} · Votes ${s.used}/${s.budget} · Contradictory pairs ${s.contradictions}\n${s.certificate ? 'Confirmation observations complete' : s.attempt ? 'Confirmation in progress' : 'Confirmation incomplete'} · ${mode} mode`;
    if (s.budget < s.required) status.textContent += `\nIncrease max_votes to at least ${s.required} to begin.`;
    if (missing) status.textContent += '\nPreview unavailable. Restore the temporary files, or run the workflow for a new tournament. History is retained.';
    if (s.result) status.textContent += `\nSelected image ${s.result.winner + 1}. Confirmation describes observed consistency, not statistical certainty.`;
    finalists.replaceChildren();
    if (s.phase === 'selection' && !s.result) for (const index of s.finalists) {
      const item = document.createElement('button');
      const entry = image(index);
      const thumb = document.createElement('img'); thumb.src = entry.img.src; thumb.style.cssText = 'width:80px;height:65px;object-fit:contain;display:block;';
      item.append(thumb, document.createTextNode(`Select image ${index+1}`));
      item.disabled = !entry.ready;
      item.onclick = () => { engine.select(index); render(); };
      finalists.append(item);
    }
    const undone = new Set(s.events.filter(e => e.type === 'undo').map(e => e.vote));
    history.textContent = s.images.map((_, i) => `Image ${i+1}: Copeland ${s.scores[i]}`).join('\n') + '\n\n' + s.events.map(e => e.type === 'vote' ? `#${e.id}${undone.has(e.id) ? ' [UNDONE]' : ''} A=${e.pair[0]+1} B=${e.pair[1]+1} → ${e.winner+1} (${e.phase})` : JSON.stringify(e)).join('\n');
    draw(); node.setDirtyCanvas?.(true, true);
  }
  canvas.onpointerenter = () => { over = true; draw(); };
  canvas.onpointerleave = () => { over = false; down = false; draw(); };
  canvas.onpointermove = e => { split = Math.max(0, Math.min(1, (e.clientX-canvas.getBoundingClientRect().left)/canvas.clientWidth)); draw(); };
  canvas.onpointerdown = e => { down = true; canvas.setPointerCapture(e.pointerId); draw(); };
  canvas.onpointerup = canvas.onpointercancel = () => { down = false; draw(); };
  const observer = new ResizeObserver(draw); observer.observe(canvas);
  const widget = node.addDOMWidget('cid_ab_comparer', 'cid_ab_comparer', root, {serialize: false, hideOnZoom: false});
  widget.computeSize = () => [380, 460];
  const budget = node.widgets.find(w => w.name === 'max_votes');
  const originalCallback = budget?.callback;
  if (budget) budget.callback = value => {
    originalCallback?.call(budget, value);
    if (engine && !engine.budget(Number(value))) budget.value = engine.s.budget;
    render();
  };
  node._cidAB = {
    load(manifest, saved = false) {
      try {
        engine = new Tournament(manifest, saved);
        if (budget) budget.value = engine.s.budget;
        if (!saved) {
          const linkId = node.inputs?.find(i => i.name === 'images')?.link;
          const link = app.graph?.links?.[linkId];
          engine.s.inputMapping = {linkId, originId: link?.origin_id, originSlot: link?.origin_slot};
        }
        render();
      } catch (error) { status.textContent = `Cannot restore tournament: ${error.message}`; }
    },
    dispose() { disposed = true; observer.disconnect(); loaded.clear(); }
  };
  render();
  return node._cidAB;
}

app.registerExtension({
  name: 'CidImageABTesting',
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== 'CidImageABTesting') return;
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function() {
      created?.apply(this, arguments);
      this.properties ||= {};
      const input = this.inputs?.find(i => i.name === 'images'); if (input) input.label = 'IMAGES';
      mountTournament(this); this.setSize([440, 570]);
    };
    const executed = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function(output) {
      executed?.apply(this, arguments);
      const manifest = output.cid_ab?.[0];
      if (manifest && manifest.id !== this.properties.cid_ab_session?.id) this._cidAB.load(manifest);
    };
    const configured = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function() {
      configured?.apply(this, arguments);
      if (this.properties.cid_ab_session) this._cidAB.load(this.properties.cid_ab_session, true);
    };
    const removed = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function() { this._cidAB?.dispose(); removed?.apply(this, arguments); };
  }
});
