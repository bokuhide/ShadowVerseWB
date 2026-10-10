import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8').replace(/^\uFEFF/, ''));
const cards = read('data/cards.json');
const metadata = read('data/metadata.json');
const recipes = read('recipes/current.json');
const research = read('research/pro/20261010.json');
const byId = new Map(cards.map(c => [c.card_id, c]));
assert.equal(cards.length, metadata.card_count);
assert.equal(byId.size, cards.length);
assert.equal(recipes.decks.length, 3);
const decks = recipes.decks.map(d => {
  assert.equal(new Set(d.cards.map(c => c.name)).size, d.cards.length);
  const total = d.cards.reduce((n, c) => n + c.count, 0);
  assert.equal(total, 40, d.name);
  for (const c of d.cards) {
    assert(Number.isInteger(c.count) && c.count >= 1 && c.count <= 3);
    const ids = c.card_id_candidates ?? [c.card_id];
    assert(ids.length > 0 && new Set(ids).size === ids.length);
    for (const id of ids) {
      const base = byId.get(id);
      assert(base, `Unknown card ${id}`);
      assert.equal(base['カード名'], c.base_name ?? c.name, `${d.name}: ${id}`);
      if (c.base_name) assert(base.card_styles.some(s => s.style_name === c.name), c.name);
    }
  }
  return { name: d.name, version: d.as_of, kinds: d.cards.length, total };
});
assert.equal(research.broadcasts.length, 8);
assert.equal(research.cases.length, 9);
for (const c of research.cases) {
  assert(c.evidence.startsWith('B'));
  assert(Number.isInteger(c.start_seconds) && c.start_seconds >= 0);
  assert(research.broadcasts.some(b => [b.main, b.audio1, b.audio2].includes(c.video)));
}
assert.equal(new Set(research.cases.map(c => c.id)).size, research.cases.length);
const publicPaths = ['AGENTS.md', 'AGENT.md', 'knowledge/handoff.md', 'recipes/current.json', 'research/pro/20261010.json', 'reports/pro_20260810-20261010.html', 'docs/cloud/README.md'];
for (const p of publicPaths) {
  const text = fs.readFileSync(path.join(root, p), 'utf8');
  assert(!/(?:\b[A-Z]:[\\/]|docs\.google\.com\/spreadsheets|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_)/i.test(text), `Potential private data in ${p}`);
}
console.log(JSON.stringify({ status: 'PASS', cardCount: cards.length, retrievedAt: metadata.retrieved_at, decks, broadcasts: research.broadcasts.length * 3, cases: research.cases.length, privacyScan: 'PASS (heuristic; curated files only)' }, null, 2));
