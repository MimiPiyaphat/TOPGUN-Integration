"""Rule-only spread1 from the isolated lab; no market or LLM calls.

Buyer-volume learning, Instant initial markup .97, RFQ ranking jitter 1%.
Uses react70's spec blacklist, pace, split and constrained allocator.
"""
import copy
import random
import re
from collections import Counter
from types import SimpleNamespace

import react70 as core


def _step(rows, k, weighted=False):
    eligible = [o for o in rows if o['status'] != 'SPEC_MISMATCH']
    total = sum(o['kg'] for o in eligible)
    if not total:
        return 0.
    if weighted:
        delta = sum(-.06 * o['kg'] if o['status'] == 'ABOVE_LIMIT'
                    else .02 * o['filled_kg'] - .03 * (o['kg'] - o['filled_kg'])
                    for o in eligible) / total
    else:
        statuses = [o['status'] for o in rows]
        lost = sum(o['kg'] - o['filled_kg'] for o in eligible
                   if o['status'] in ('OUTBID', 'PARTIAL')) / total
        delta = (-.06 if 'ABOVE_LIMIT' in statuses else
                 -.03 * (1.5 if lost >= .7 else 1.)
                 if any(s in statuses for s in ('OUTBID', 'PARTIAL')) else
                 .02 if all(s == 'ACCEPTED' for s in statuses) else 0.)
    return delta * k


def decide(state, ctx):
    memory = ctx.memory
    saved = getattr(memory, 'policy_state', {}).get('spread1', {})
    rng = random.Random()
    rng.setstate(core.tuples(saved.get('jitter_state', ctx.rng.getstate())))
    rounds = list(getattr(memory, 'rounds', []))
    last = state.get('last_results')
    if last and not any(r.get('round_id') == last.get('round_id') for r in rounds):
        rounds.append(last)
    # Isolate random state from react70 so switching strategies preserves both.
    proxy = SimpleNamespace(rounds=rounds, sent=getattr(memory, 'sent', {}),
                            policy_state={'react70': {'rng_state': saved.get('rng_state', rng.getstate())}})
    local = copy.copy(ctx)
    local.memory = proxy
    candidates, budget, _, rng_state = core.prepare(state, local)
    mt = {t: (.97 if t == 'INSTANT' else 1.) for t in core.TYPES}
    mb, evidence, seen = {}, Counter(), set()
    for result in rounds:
        rid = result.get('round_id')
        if not rid or rid in seen:
            continue
        seen.add(rid)
        sent = {(o['rfq_id'], o['lot_id']): o for o in proxy.sent.get(rid, [])}
        gt, gb = {}, {}
        for row in result.get('my_offers', []):
            prior = sent.get((row['rfq_id'], row['lot_id']))
            if prior is None:
                continue
            gt.setdefault(prior['buyer_type'], []).append(row)
            gb.setdefault((prior['buyer'], prior['buyer_type']), []).append(row)
        number = re.search(r'(\d+)$', str(rid))
        completed = int(number.group(1)) if number else len(seen)
        k = max(.5, 1.5 - completed / ctx.rules['timeline']['rounds'])
        for kind, rows in gt.items():
            mt[kind] = min(1.3, max(.85, mt.get(kind, 1.) + _step(rows, k)))
        for (buyer, kind), rows in gb.items():
            initial = .97 if kind == 'INSTANT' else 1.
            mb[buyer] = min(1.3, max(.85, mb.get(buyer, initial) + _step(rows, k, True)))
            if any(o['status'] != 'SPEC_MISMATCH' for o in rows):
                evidence[buyer] += 1
    for c in candidates:
        m = mt[c['buyer_type']]
        if c['buyer'] in mb:
            w = evidence[c['buyer']] / (evidence[c['buyer']] + 2.)
            m = w * mb[c['buyer']] + (1 - w) * m
        c.update(markup=m, price_per_kg=round(c['tv'] * m, 2))
        c['_score'] = c['tv'] * m * (1 + rng.uniform(-.01, .01))
    candidates.sort(key=lambda c: -c['_score'])
    for i, c in enumerate(candidates):
        c['candidate'] = i
    offers = core.allocate(state, candidates, budget)
    if memory is not None:
        if not hasattr(memory, 'policy_state'):
            memory.policy_state = {}
        memory.policy_state['spread1'] = dict(rng_state=rng_state, jitter_state=rng.getstate())
        memory.save()
    ctx.rng.setstate(rng.getstate())
    ctx.notes.append('spread1: buyer-volume learning; Instant=.97 initially; ranking jitter=1%; pace=2; split=.5')
    ctx.notes.append('spread1 type markups: ' + str(mt))
    return offers, 'spread1_rules'
