// Pure tournament reducer. No ComfyUI or browser dependencies.
const copy = (x) => JSON.parse(JSON.stringify(x));
const key = (a, b) => [a, b].sort((x, y) => x - y).join(':');
export class Tournament {
  constructor(manifest, saved = false) {
    if (saved) {
      if (manifest.version !== 1) throw new Error('Unsupported tournament version');
      this.s = copy(manifest);
      this.refresh();
      return;
    }
    this.s = {version: 1, id: manifest.id, images: manifest.images, budget: manifest.budget,
      rng: manifest.seed ?? Math.floor(Math.random() * 4294967295), events: [], nextId: 1,
      phase: 'round_robin', queue: [], attempt: null, certificate: null, result: null};
    const pairs = [];
    for (let a = 0; a < this.s.images.length; a++)
      for (let b = a + 1; b < this.s.images.length; b++) pairs.push(this.orient(a, b));
    this.s.queue = this.shuffle(pairs);
    if (this.s.images.length === 1) this.s.result = {winner: 0, label: 'Only candidate', method: 'single'};
    this.refresh();
  }
  random() {
    this.s.rng = (Math.imul(this.s.rng, 1664525) + 1013904223) >>> 0;
    return this.s.rng / 4294967296;
  }
  shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(this.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }
  orient(a, b) { return this.random() < .5 ? [a, b] : [b, a]; }
  get votes() {
    const undone = new Set(this.s.events.filter(e => e.type === 'undo').map(e => e.vote));
    return this.s.events.filter(e => e.type === 'vote' && !undone.has(e.id));
  }
  refresh() {
    const n = this.s.images.length;
    this.counts = Array.from({length: n}, () => Array(n).fill(0));
    this.initial = new Map();
    for (const v of this.votes) {
      this.counts[v.winner][v.pair.find(i => i !== v.winner)]++;
      if (v.phase === 'round_robin') this.initial.set(key(...v.pair), v);
    }
    this.s.scores = this.counts.map((row, i) => row.reduce((sum, wins, j) => sum + (i !== j && wins > this.counts[j][i] ? 1 : 0), 0));
    this.s.used = this.votes.length;
    this.s.coverage = this.initial.size;
    this.s.required = n * (n - 1) / 2;
    this.s.contradictions = 0;
    for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++)
      if (this.counts[a][b] && this.counts[b][a]) this.s.contradictions++;
    this.s.initialWinner = null;
    if (this.s.coverage === this.s.required) {
      for (let a = 0; a < n; a++) {
        if (this.s.images.every((_, b) => a === b || this.initial.get(key(a, b))?.winner === a)) this.s.initialWinner = a;
      }
    }
    this.s.aggregateWinner = this.s.scores.findIndex(score => score === n - 1);
    // Derived confirmation is never trusted from serialized result caches.
    if (this.s.result?.method === 'confirmed' && !this.canConfirm(this.s.result.winner)) this.s.result = null;
    this.s.complete = !!this.s.result;
  }
  canConfirm(candidate) {
    const cert = this.s.certificate;
    if (!cert || cert.candidate !== candidate || this.s.aggregateWinner !== candidate) return false;
    const fresh = this.votes.filter(v => v.id >= cert.start && v.pair.includes(candidate));
    if (fresh.some(v => v.winner !== candidate)) return false;
    return this.s.images.every((_, rival) => {
      if (rival === candidate) return true;
      const matches = fresh.filter(v => v.pair.includes(rival));
      return cert.kind === 'clean' ? matches.length >= 1 && matches.some(v => v.pair[0] === this.initial.get(key(candidate, rival)).pair[1])
        : matches.some(v => v.pair[0] === candidate) && matches.some(v => v.pair[1] === candidate);
    });
  }
  leaders() { const max = Math.max(...this.s.scores); return this.s.scores.flatMap((v, i) => v === max ? [i] : []); }
  balanced(a, b) {
    const previous = this.votes.filter(v => key(...v.pair) === key(a, b));
    const left = previous.filter(v => v.pair[0] === a).length;
    if (2 * left === previous.length) return this.orient(a, b);
    return 2 * left > previous.length ? [b, a] : [a, b];
  }
  startAttempt(candidate, kind) {
    const rivals = this.shuffle(this.s.images.flatMap((_, i) => i === candidate ? [] : [i]));
    let pairs = rivals.map(r => kind === 'clean' ? [...this.initial.get(key(candidate, r)).pair].reverse() : this.balanced(candidate, r));
    if (kind !== 'clean') pairs = [...pairs, ...this.shuffle(pairs.map(p => [...p].reverse()))];
    this.s.attempt = {candidate, kind, start: this.s.nextId};
    this.s.phase = 'confirmation';
    this.s.queue = pairs;
  }
  advance() {
    this.refresh();
    if (this.s.certificate && this.canConfirm(this.s.certificate.candidate)) {
      const {candidate, kind} = this.s.certificate;
      this.s.complete = true;
      this.s.result = {winner: candidate, method: 'confirmed', label: `Confirmed Condorcet Winner — ${kind === 'clean' ? 'clean confirmation' : 'reconfirmed'}`};
      return;
    }
    if (this.s.used >= this.s.budget) { this.end(); return; }
    if (this.s.queue.length) return;
    if (this.s.phase === 'round_robin' && this.s.initialWinner !== null) {
      this.startAttempt(this.s.initialWinner, 'clean'); return;
    }
    this.s.phase = 'adaptive';
    const leaders = this.leaders();
    if (!this.s.certificate && leaders.length === 1 && this.s.budget - this.s.used >= 2 * (this.s.images.length - 1)) {
      this.startAttempt(leaders[0], 'fresh'); return;
    }
    const pairs = [];
    for (let a = 0; a < this.s.images.length; a++) for (let b = a + 1; b < this.s.images.length; b++) {
      if (!leaders.includes(a) && !leaders.includes(b)) continue;
      const x = this.counts[a][b], y = this.counts[b][a];
      const c = this.s.certificate?.candidate;
      const deficit = c !== undefined && (a === c || b === c) && this.counts[c][a === c ? b : a] <= this.counts[a === c ? b : a][c];
      pairs.push({a, b, rank: [deficit ? 0 : 1, leaders.includes(a) && leaders.includes(b) ? 0 : 1,
        -Math.min(this.s.scores[a], this.s.scores[b]), x === y ? 0 : x && y ? 1 : 2, Math.abs(x-y), x+y, this.random()]});
    }
    pairs.sort((p, q) => { for (let i = 0; i < p.rank.length; i++) if (p.rank[i] !== q.rank[i]) return p.rank[i] - q.rank[i]; return 0; });
    this.s.queue = [this.balanced(pairs[0].a, pairs[0].b)];
  }
  get current() { return this.s.result || this.s.phase === 'selection' ? null : this.s.queue[0]; }
  vote(winner) {
    const pair = this.current;
    if (!pair || !pair.includes(winner) || this.s.used >= this.s.budget || this.s.budget < this.s.required) return false;
    const before = copy({phase: this.s.phase, queue: this.s.queue, attempt: this.s.attempt, certificate: this.s.certificate, rng: this.s.rng});
    this.s.events.push({type: 'vote', id: this.s.nextId++, pair: [...pair], winner, phase: this.s.phase, before});
    this.s.queue.shift();
    if (this.s.certificate && pair.includes(this.s.certificate.candidate) && winner !== this.s.certificate.candidate) this.s.certificate = null;
    if (this.s.attempt) {
      if (winner !== this.s.attempt.candidate) { this.s.attempt = null; this.s.queue = []; this.s.phase = 'adaptive'; }
      else if (!this.s.queue.length) { this.s.certificate = this.s.attempt; this.s.attempt = null; }
    }
    this.advance(); return true;
  }
  end() {
    this.refresh();
    if (this.s.coverage < this.s.required) {
      this.s.phase = 'selection'; this.s.finalists = this.s.images.map((_, i) => i); return;
    }
    const leaders = this.leaders();
    if (leaders.length > 1) { this.s.phase = 'selection'; this.s.finalists = leaders; return; }
    const winner = leaders[0];
    this.s.complete = true;
    this.s.result = {winner, method: 'copeland', label: winner === this.s.initialWinner ? 'Observed Condorcet Winner — provisional' : 'Provisional Copeland Winner'};
  }
  select(winner) {
    if (this.s.phase !== 'selection' || !this.s.finalists.includes(winner)) return;
    const incomplete = this.s.coverage < this.s.required;
    this.s.complete = true;
    this.s.result = {winner, method: incomplete ? 'human_incomplete' : 'human_tie', label: incomplete ? 'Human Selection — incomplete round-robin' : 'Human Tie-Break Winner'};
    this.s.events.push({type: 'selection', id: this.s.nextId++, ...this.s.result});
  }
  undo() {
    const vote = this.votes.at(-1);
    if (!vote) return false;
    this.s.events.push({type: 'undo', id: this.s.nextId++, vote: vote.id, invalidatesSelectionsAfter: vote.id});
    Object.assign(this.s, copy(vote.before), {result: null, finalists: []});
    this.refresh(); return true;
  }
  budget(value) {
    if (!Number.isInteger(value) || value < Math.max(1, this.s.used)) return false;
    this.s.budget = value; return true;
  }
  resume() {
    if (this.s.result?.method === 'confirmed' || this.s.result?.method === 'single' || this.s.used >= this.s.budget) return;
    this.s.result = null; this.s.complete = false; this.s.finalists = [];
    this.s.events.push({type: 'resume', id: this.s.nextId++});
    if (this.s.coverage < this.s.required) this.s.phase = 'round_robin';
    else if (this.s.phase === 'selection') this.s.phase = this.s.attempt ? 'confirmation' : 'adaptive';
    this.advance();
  }
}
