"""Live react70: host pricing, constrained LLM allocation, rule fallback.
No simulator imports or global patches. Feedback replay survives restarts.
"""
import json
import math
import random
import re
import time
from pathlib import Path
import strategy as base

BAG = 60
TYPES = ('SPECIALTY', 'COMMERCIAL', 'INSTANT')
SYSTEM = Path(__file__).with_name('prompts').joinpath('react70_system.txt').read_text(encoding='utf-8')
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['offers', 'reason'],
          'properties': {'offers': {'type': 'array', 'items': {
              'type': 'object', 'additionalProperties': False, 'required': ['candidate', 'bags'],
              'properties': {'candidate': {'type': 'integer', 'minimum': 0},
                             'bags': {'type': 'integer', 'minimum': 1}}}},
                         'reason': {'type': 'string', 'maxLength': 300}}}


def learned(state, ctx):
    mt = {t: 1.0 for t in TYPES}
    bad, history, seen = [], [], set()
    rounds = list(getattr(ctx.memory, 'rounds', []))
    last = state.get('last_results')
    if last and not any(r.get('round_id') == last.get('round_id') for r in rounds):
        rounds.append(last)
    total = ctx.rules['timeline']['rounds']
    for result in rounds:
        rid = result.get('round_id')
        if not rid or rid in seen:
            continue
        seen.add(rid)
        sent = {(o['rfq_id'], o['lot_id']): o for o in getattr(ctx.memory, 'sent', {}).get(rid, [])}
        groups = {}
        for o in result.get('my_offers', []):
            prior = sent.get((o['rfq_id'], o['lot_id']))
            if not prior:
                continue
            if o['status'] == 'SPEC_MISMATCH' and 'spec' in prior:
                pair = (o['lot_id'], prior['spec'])
                if pair not in bad:
                    bad.append(pair)
            groups.setdefault(prior['buyer_type'], []).append(o)
        number = re.search(r'(\d+)$', str(rid))
        completed = int(number.group(1)) if number else len(seen)
        k = max(.5, 1.5 - completed / total)
        evidence = {}
        for kind, rows in groups.items():
            statuses = [o['status'] for o in rows]
            eligible = [o for o in rows if o['status'] != 'SPEC_MISMATCH']
            kg = sum(o['kg'] for o in eligible)
            lost = sum(o['kg'] - o['filled_kg'] for o in eligible if o['status'] in ('OUTBID', 'PARTIAL'))
            ratio = lost / kg if kg else 0.
            if 'ABOVE_LIMIT' in statuses:
                delta = -.06
            elif 'OUTBID' in statuses or 'PARTIAL' in statuses:
                delta = -.03 * (1.5 if ratio >= .70 else 1.)
            elif statuses and all(s == 'ACCEPTED' for s in statuses):
                delta = .02
            else:
                delta = 0.
            mt[kind] = min(1.30, max(.85, mt.get(kind, 1.) + delta * k))
            evidence[kind] = dict(eligible_kg=kg, lost_competition_kg=lost,
                                  loss_fraction=ratio, markup=mt[kind], delta=delta*k)
        history.append(dict(round_id=rid, by_type=evidence,
                            my_offers=result.get('my_offers', []),
                            market_summary=result.get('market_summary', [])))
    return mt, bad, history


def blocked(lid, spec, bad):
    return any(lid == old_id and spec['max_defect_pct'] <= old['max_defect_pct']
               and spec['max_moisture_pct'] <= old['max_moisture_pct']
               and (spec['min_screen'] or 0) >= (old['min_screen'] or 0)
               for old_id, old in bad)


def tuples(value):
    return tuple(tuples(v) for v in value) if isinstance(value, list) else value


def prepare(state, ctx):
    mt, bad, history = learned(state, ctx)
    left = base.rounds_left(state, ctx)
    budget = {}
    for lot in state['lots']:
        avail = lot['kg_available'] // BAG
        budget[lot['lot_id']] = min(avail, max(1, math.ceil(avail / max(1, left) * 2))) if avail else 0
    rng = random.Random(11)
    saved = getattr(ctx.memory, 'policy_state', {}).get('react70', {})
    if saved.get('rng_state'):
        rng.setstate(tuples(saved['rng_state']))
    weighted = []
    for lot in state['lots']:
        if not budget[lot['lot_id']]:
            continue
        for rfq in state['rfqs']:
            if not base.spec_ok(lot['sample'], rfq['spec']):
                continue
            c = dict(lot_id=lot['lot_id'], rfq_id=rfq['rfq_id'], buyer=rfq['buyer'],
                     buyer_type=rfq['buyer_type'], tv=ctx.tv[lot['lot_id']],
                     markup=mt.get(rfq['buyer_type'], 1.), rfq_bags=rfq['bags'],
                     max_bags=min(budget[lot['lot_id']], rfq['bags'], max(1, math.ceil(budget[lot['lot_id']] * .5))))
            weighted.append((rng.random() ** (1 / rfq['bags']), c, rfq['spec']))
    cands = [c for _, c, spec in sorted(weighted, key=lambda x: -x[0]) if not blocked(c['lot_id'], spec, bad)]
    cands.sort(key=lambda c: -c['tv'] * c['markup'])
    for i, c in enumerate(cands):
        c.update(candidate=i, price_per_kg=round(c['tv'] * c['markup'], 2))
    return cands, budget, history, rng.getstate()


def allocate(state, cands, budget, requested=None):
    """Validate whole LLM plan; fill remainder using the rule ordering."""
    lot_left = dict(budget)
    rfq_left = {r['rfq_id']: r['bags'] for r in state['rfqs']}
    capacity = state.get('capacity_left_kg')
    room = sum(budget.values()) if capacity is None else max(0, capacity // BAG)
    seen, offers = set(), []
    def add(index, bags):
        nonlocal room
        c = cands[index]
        offers.append(dict(lot_id=c['lot_id'], rfq_id=c['rfq_id'], kg=bags*BAG,
                           price_per_kg=c['price_per_kg']))
        seen.add(index)
        room -= bags
        lot_left[c['lot_id']] -= bags
        rfq_left[c['rfq_id']] -= bags
    def limit(c):
        return min(room, lot_left[c['lot_id']], rfq_left[c['rfq_id']], c['max_bags'])
    if requested is not None:
        if not isinstance(requested, dict) or set(requested) != {'offers', 'reason'}:
            raise ValueError('invalid JSON keys')
        if not isinstance(requested['reason'], str) or len(requested['reason']) > 300 or not isinstance(requested['offers'], list):
            raise ValueError('invalid reason/offers')
        for row in requested['offers']:
            if not isinstance(row, dict) or set(row) != {'candidate', 'bags'}:
                raise ValueError('LLM may only choose candidate and bags')
            i, bags = row['candidate'], row['bags']
            if type(i) is not int or type(bags) is not int or not 0 <= i < len(cands) or i in seen:
                raise ValueError('invalid or duplicate candidate')
            if bags < 1 or bags > limit(cands[i]):
                raise ValueError('allocation exceeds capacity, lot, RFQ or split budget')
            add(i, bags)
    for i, c in enumerate(cands):
        if i not in seen and limit(c) > 0:
            add(i, limit(c))
    return offers


def decide(state, ctx):
    start = time.monotonic()
    cands, budget, history, rng_state = prepare(state, ctx)
    fallback = allocate(state, cands, budget)
    payload = dict(round=state['round'], capacity_left_kg=state.get('capacity_left_kg'),
                   lot_budget_bags=budget, calendar=ctx.calendar, candidates=cands,
                   baseline_offers=fallback, recent_results=history[-3:])
    payload['lots'] = [{k: l[k] for k in ('lot_id', 'kg_total', 'kg_available', 'sample')} for l in state['lots']]
    offers, source = fallback, 'react70_rules'
    allowance = max(0., ctx.seconds_left - (time.monotonic()-start) - 5.)
    if ctx.pricing_mode == 'react70_llm' and ctx.llm and cands and fallback and allowance >= 3:
        try:
            answer = ctx.llm.ask_json(SYSTEM, json.dumps(payload, ensure_ascii=False), SCHEMA, timeout=allowance)
            if time.monotonic()-start > ctx.seconds_left-5:
                raise ValueError('LLM exceeded decision deadline')
            if answer is None:
                raise ValueError('LLM unavailable or invalid JSON')
            offers = allocate(state, cands, budget, answer)
            source = 'react70_llm' if answer['offers'] else 'react70_rules'
            ctx.notes.append('Qwen allocation: '+answer['reason'])
        except Exception as exc:
            offers = fallback
            ctx.notes.append('react70 fallback: '+str(exc)[:200])
    elif ctx.pricing_mode == 'react70_llm':
        ctx.notes.append('react70 fallback: LLM disabled, no feasible offer, or insufficient time')
    if ctx.memory is not None:
        if not hasattr(ctx.memory, 'policy_state'):
            ctx.memory.policy_state = {}
        ctx.memory.policy_state['react70'] = dict(rng_state=rng_state)
        ctx.memory.save()
    ctx.notes.append('react70: fixed prices; 70% threshold; pace=2; split=0.5')
    return offers, source
