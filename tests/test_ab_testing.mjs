import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Tournament} from '../js/cid_image_ab_testing_engine.mjs';
const create = (n=5,budget=30) => new Tournament({id:'test',seed:123,budget,images:Array.from({length:n},(_,i)=>({id:`image${i}`}))});
const restore = t => new Tournament(JSON.parse(JSON.stringify(t.s)), true);
function initial(t, decide = p => Math.min(...p)) { for(let i=0;i<t.s.required;i++) assert.ok(t.vote(decide(t.current))); }

test('complete unique round robin and clean confirmation, 5 and 6 images',()=>{
  for(const n of [5,6]) {
    const t=create(n); initial(t);
    assert.equal(t.s.coverage,n*(n-1)/2); assert.equal(t.s.initialWinner,0);
    while(!t.s.result) t.vote(0);
    assert.equal(t.s.result.method,'confirmed'); assert.equal(t.s.used,t.s.required+n-1);
    assert.ok(restore(t).canConfirm(0));
  }
});
test('early ending asks for a human selection from everyone, including zero votes',()=>{
  const t=create(); t.end(); assert.deepEqual(t.s.finalists,[0,1,2,3,4]);
  t.select(4); assert.equal(t.s.result.method,'human_incomplete');
  t.budget(40); t.resume(); t.vote(Math.min(...t.current)); t.end();
  assert.equal(t.s.result,null); assert.equal(t.s.finalists.length,5);
});
test('undo refunds budget, restores exact pair and survives serialization',()=>{
  const t=create(); const pair=[...t.current]; t.vote(pair[0]);
  assert.ok(t.undo()); assert.equal(t.s.used,0); assert.equal(t.s.coverage,0); assert.deepEqual(t.current,pair);
  const r=restore(t); assert.deepEqual(r.current,pair); r.vote(pair[1]);
  assert.equal(r.s.used,1); assert.equal(r.s.events.filter(e=>e.type==='vote').length,2);
  r.undo(); assert.equal(r.s.used,0); assert.equal(r.undo(),false);
});
test('undo completion revokes confirmation and restores its final matchup',()=>{
  const t=create(3); initial(t); while(!t.s.result) t.vote(0);
  const last=t.votes.at(-1); t.undo(); assert.equal(t.s.result,null);
  assert.deepEqual(t.current,last.pair); assert.equal(t.s.used,4); t.vote(0); assert.ok(t.canConfirm(0));
});
test('fresh certificate cannot override an aggregate loss or tie',()=>{
  const t=create(2,30); t.s.events=[];
  for(let i=1;i<=5;i++) t.s.events.push({type:'vote',id:i,pair:[0,1],winner:1,phase:i===1?'round_robin':'adaptive'});
  t.s.events.push({type:'vote',id:6,pair:[0,1],winner:0,phase:'confirmation'}, {type:'vote',id:7,pair:[1,0],winner:0,phase:'confirmation'});
  t.s.certificate={candidate:0,kind:'fresh',start:6}; t.s.nextId=8; t.refresh();
  assert.equal(t.canConfirm(0),false);
  for(let i=8;i<=10;i++) t.s.events.push({type:'vote',id:i,pair:[0,1],winner:0,phase:'adaptive'});
  t.refresh(); assert.equal(t.canConfirm(0),false);
  t.s.events.push({type:'vote',id:11,pair:[1,0],winner:0,phase:'adaptive'}); t.refresh(); assert.equal(t.canConfirm(0),true);
  t.s.events.push({type:'vote',id:12,pair:[1,0],winner:1,phase:'adaptive'}); t.refresh(); assert.equal(t.canConfirm(0),false);
});
test('cycles respect cap and require a separate human tie break',()=>{
  const t=create(3,3); const win=p=>p.includes(0)&&p.includes(2)?2:Math.min(...p);
  initial(t,win); assert.equal(t.s.phase,'selection'); assert.equal(t.s.used,3);
  assert.equal(t.vote(0),false); t.select(1); assert.equal(t.s.result.method,'human_tie'); assert.equal(t.s.used,3);
  t.undo(); assert.equal(t.s.result,null); assert.equal(t.s.used,2);
});
test('failed confirmation preserves history; fresh attempt permits recovery',()=>{
  const t=create(3); initial(t); const rival=t.current.find(i=>i!==0); t.vote(rival);
  assert.equal(t.s.contradictions,1); let guard=0;
  while(!t.s.result && t.s.phase!=='selection' && guard++<30) t.vote(Math.min(...t.current));
  assert.equal(t.s.result.method,'confirmed'); assert.match(t.s.result.label,/reconfirmed/);
  assert.equal(t.s.contradictions,1); assert.ok(t.s.used<=30);
});
test('insufficient starting budget blocks votes; increasing preserves schedule',()=>{
  const t=create(6,10); const pair=[...t.current]; assert.equal(t.vote(pair[0]),false);
  t.budget(30); assert.deepEqual(t.current,pair); assert.ok(t.vote(pair[0])); assert.equal(t.budget(0),false);
});
test('randomized sessions survive restore at each step and never exceed cap',()=>{
  for(let seed=1;seed<=50;seed++) {
    let t=create(6); t.s.rng=seed;
    for(let i=0;i<35 && !t.s.result && t.s.phase!=='selection';i++) {
      const p=t.current; assert.ok(p); assert.ok(t.vote(p[(seed+i)%2])); t=restore(t);
      assert.ok(t.s.used<=t.s.budget);
      if(t.s.result?.method==='confirmed') assert.ok(t.canConfirm(t.s.result.winner));
    }
    assert.ok(t.s.result || t.s.phase==='selection');
  }
});

test('resume a paused tied confirmation retains its phase and attempt',()=>{
  const t=create(3); initial(t); t.vote(0); t.end();
  const queue=JSON.stringify(t.s.queue), attempt=JSON.stringify(t.s.attempt);
  t.resume(); assert.equal(t.s.phase,'confirmation');
  assert.equal(JSON.stringify(t.s.queue),queue); assert.equal(JSON.stringify(t.s.attempt),attempt);
  t.vote(0); assert.equal(t.s.result.method,'confirmed');
});
test('budget exhaustion with an initial winner stays provisional until extension',()=>{
  const t=create(5,10); initial(t); assert.equal(t.s.result.method,'copeland');
  assert.match(t.s.result.label,/Observed/); assert.equal(t.s.used,10);
  t.budget(30);t.resume();while(!t.s.result)t.vote(0);
  assert.equal(t.s.result.method,'confirmed');assert.equal(t.s.used,14);
});
test('different seeds change pair placement or order; Undo keeps changed budget',()=>{
  const t=create(),other=new Tournament({id:'other',seed:77,budget:30,images:t.s.images});
  assert.notEqual(JSON.stringify(t.s.queue),JSON.stringify(other.s.queue));
  const schedule=JSON.stringify(t.s.queue);t.vote(t.current[0]);t.budget(50);t.undo();
  assert.equal(t.s.budget,50);assert.equal(JSON.stringify(t.s.queue),schedule);
});
