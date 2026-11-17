import copy
import json
import random
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import react70 as R
import strategy
from memory import Memory

def fixture():
    spec = dict(max_defect_pct=8., max_moisture_pct=13., min_screen=None)
    state = dict(round=dict(round_id='R1', kind='real', number=1, of=8), capacity_left_kg=360,
                 last_results=None, lots=[dict(lot_id='L1', kg_total=360, kg_available=360,
                 sample=dict(defect_pct=4., moisture_pct=12., screen=14))],
                 rfqs=[dict(rfq_id=f'R1-{i}', buyer=f'b{i}', buyer_type='COMMERCIAL', bags=8, kg=480, spec=spec) for i in range(4)])
    mem = SimpleNamespace(sent={}, rounds=[], policy_state={}, save=lambda: None)
    ctx = strategy.Context({'timeline': {'rounds': 8}}, [], {'L1': 100.}, random.Random(1), mem, None, 99, 'react70_llm')
    return state, ctx

class Reply:
    def __init__(self, answer): self.answer=answer; self.calls=0
    def ask_json(self, system, user, schema, timeout):
        self.calls+=1; self.payload=json.loads(user)
        if isinstance(self.answer, Exception): raise self.answer
        return self.answer

class Tests(unittest.TestCase):
    def test_learning_threshold_priority_and_exclusion(self):
        state, ctx=fixture()
        spec=state['rfqs'][0]['spec']
        def learn(statuses):
            ctx.memory.sent={'R1':[dict(rfq_id=str(i), lot_id='L1', buyer_type='COMMERCIAL', spec=spec) for i in range(len(statuses))]}
            ctx.memory.rounds=[dict(round_id='R1',my_offers=[dict(rfq_id=str(i),lot_id='L1',status=s,kg=kg,filled_kg=fill) for i,(s,kg,fill) in enumerate(statuses)])]
            return R.learned(state,ctx)[0]['COMMERCIAL']
        self.assertAlmostEqual(learn([('PARTIAL',600,180)]),1-.03*1.5*1.375)
        self.assertAlmostEqual(learn([('PARTIAL',600,240)]),1-.03*1.375)
        self.assertAlmostEqual(learn([('OUTBID',60,0),('SPEC_MISMATCH',600,0)]),1-.03*1.5*1.375)
        self.assertAlmostEqual(learn([('OUTBID',600,0),('ABOVE_LIMIT',60,0)]),1-.06*1.375)
        self.assertAlmostEqual(learn([('ACCEPTED',60,60)]),1+.02*1.375)
        self.assertEqual(learn([('SPEC_MISMATCH',60,0)]),1.)
    def test_duplicate_feedback(self):
        state,ctx=fixture()
        ctx.memory.sent={'R1':[dict(rfq_id='x',lot_id='L1',buyer_type='COMMERCIAL')]}
        result=dict(round_id='R1',my_offers=[dict(rfq_id='x',lot_id='L1',kg=60,filled_kg=0,status='OUTBID')])
        ctx.memory.rounds=[result,result]; state['last_results']=result
        self.assertAlmostEqual(R.learned(state,ctx)[0]['COMMERCIAL'],1-.03*1.5*1.375)
    def test_blacklist_stricter_only(self):
        spec=dict(max_defect_pct=8,max_moisture_pct=13,min_screen=13)
        self.assertTrue(R.blocked('L1',dict(max_defect_pct=7,max_moisture_pct=12.5,min_screen=14),[('L1',spec)]))
        self.assertFalse(R.blocked('L1',dict(max_defect_pct=9,max_moisture_pct=12.5,min_screen=14),[('L1',spec)]))
    def test_invalid_outputs_exact_fallback(self):
        bad=[None,{},dict(offers=[dict(candidate=-1,bags=1)],reason='x'),
             dict(offers=[dict(candidate=0,bags=1,markup=.85)],reason='x'),
             dict(offers=[dict(candidate=0,bags=999)],reason='x'),
             dict(offers=[dict(candidate=True,bags=1)],reason='x'),
             dict(offers=[dict(candidate=0,bags=1),dict(candidate=0,bags=1)],reason='x'),
             dict(offers=[dict(candidate=0,bags=1.5)],reason='x'),TimeoutError('timeout')]
        for answer in bad:
            with self.subTest(answer=answer):
                state,ctx=fixture(); c,b,_,_=R.prepare(state,ctx); expected=R.allocate(state,c,b)
                ctx.llm=Reply(answer)
                actual,source=strategy.decide(state,ctx)
                self.assertEqual(actual,expected); self.assertEqual(source,'react70_rules')
    def test_valid_llm_and_fill_and_no_actual(self):
        state,ctx=fixture(); state['lots'][0]['actual']={'secret':True}
        ctx.llm=Reply(dict(offers=[dict(candidate=2,bags=1)],reason='diversify'))
        actual,source=strategy.decide(state,ctx)
        self.assertEqual(source,'react70_llm'); self.assertEqual(sum(o['kg'] for o in actual),120)
        self.assertTrue(all(o['price_per_kg']==100 for o in actual))
        self.assertNotIn('actual',ctx.llm.payload['lots'][0])
        self.assertEqual(len({(o['lot_id'],o['rfq_id']) for o in actual}),len(actual))
    def test_low_time_and_zero_capacity_skip_llm(self):
        for seconds,capacity in ((0,360),(7,360),(99,0)):
            state,ctx=fixture(); ctx.seconds_left=seconds; state['capacity_left_kg']=capacity
            ctx.llm=Reply(None); strategy.decide(state,ctx)
            self.assertEqual(ctx.llm.calls,0)
    def test_restart_rng_and_feedback(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            state,ctx=fixture(); ctx.memory=Memory(Path(temp)/'m.json')
            offers,_=strategy.decide(state,ctx)
            ctx.memory.record_sent('R1',offers,state,ctx.tv)
            saved=Memory(ctx.memory.path)
            c1,b1,_,_=R.prepare(state,ctx); ctx.memory=saved
            c2,b2,_,_=R.prepare(state,ctx)
            self.assertEqual((c1,b1),(c2,b2))
    def test_late_reply_uses_fallback(self):
        state,ctx=fixture(); c,b,_,_=R.prepare(state,ctx); expected=R.allocate(state,c,b)
        ctx.llm=Reply(dict(offers=[dict(candidate=2,bags=1)],reason='late'))
        with patch('react70.time.monotonic',side_effect=[0.,0.,100.]):
            actual,source=R.decide(state,ctx)
        self.assertEqual(actual,expected); self.assertEqual(source,'react70_rules')

if __name__=='__main__': unittest.main()
