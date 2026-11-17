"""Isolated fast market study. Frozen live react70 baseline. No network calls.
Run with D:\\Coffee-TESA-starter\\.venv\\Scripts\\python.exe -B experiment.py search
"""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE/'frozen'))
import json,random,math,copy,collections,statistics,hashlib,concurrent.futures
from types import SimpleNamespace
import react70 as core
import strategy
from appraisal import true_value,estimate_lots

FIELDS={
 'sandbox':{},
 'scarce':dict(demand=.5),
 'abundant':dict(demand=1.5),
 'heterogeneous':dict(spread=.08),
 'low_ceiling':dict(shift=-.05),
 'high_ceiling':dict(shift=.05),
 'flat':dict(flat=True),
 'shared_noise':dict(noise=.45),
 'day18_56':dict(n=56,rounds=8,cap=True,specialty=True,noise=.45),
 'day18_noise':dict(n=56,rounds=8,cap=True,specialty=True,noise=.9),
 'copies':dict(copies=True),
}
POLICIES=('react70','volume','buyer','buyer_pure','market','buyer_market','buyer_volume','buyer_start')
BASE_FIELDS=list(FIELDS)
FIELDS.update({'strong_rivals':dict(rivals='buyer_start'),
               'strong_56':dict(n=56,rounds=8,cap=True,specialty=True,noise=.45,rivals='buyer_volume')})

def bootstrap():
 logs=HERE.parent/'logs'; sizes=[]; specs={}; snapshots=[]
 for p in sorted(logs.glob('memory-*.json')):
  try: d=json.loads(p.read_text(encoding='utf-8'))
  except json.JSONDecodeError: continue
  snapshots.append(dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  for offers in d['sent'].values():
   for o in offers:
    if 'spec' in o: specs[o['buyer_type']]=o['spec']
  for r in d['rounds']:
   sizes.extend(x['wanted_kg']//60 for x in r['market_summary'])
 snap=json.loads((HERE/'market_snapshot.json').read_text(encoding='utf-8'))
 hashes={n:hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest() for n in ('main.py','strategy.py','react70.py','memory.py','appraisal.py')}
 data=dict(rules=snap['calendar']['body']['rules'],sizes=sizes,specs=specs,source_memories=snapshots,production_hashes=hashes)
 (HERE/'inputs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def step(rows,k,weighted=False):
 statuses=[o['status'] for o in rows]
 eligible=[o for o in rows if o['status']!='SPEC_MISMATCH']
 total=sum(o['kg'] for o in eligible)
 if not total: return 0.
 loss=sum(o['kg']-o['filled_kg'] for o in eligible if o['status'] in ('OUTBID','PARTIAL'))/total
 if weighted:
  delta=sum((-.06*o['kg'] if o['status']=='ABOVE_LIMIT' else .02*o['filled_kg']-.03*(o['kg']-o['filled_kg'])) for o in eligible)/total
 else:
  delta=-.06 if 'ABOVE_LIMIT' in statuses else -.03*(1.5 if loss>=.7 else 1.) if any(s in statuses for s in ('OUTBID','PARTIAL')) else .02 if all(s=='ACCEPTED' for s in statuses) else 0.
 return delta*k

def decide(state,ctx,policy):
 if policy=='react70': return core.decide(state,ctx)[0]
 variant=policy
 if policy.startswith('spread'):
  policy='buyer_combo97'
  if not ctx.memory.policy_state.get('react70'):
   ctx.memory.policy_state['react70']=dict(rng_state=ctx.rng.getstate())
 candidates,budget,history,rngstate=core.prepare(state,ctx)
 mt={t:1. for t in core.TYPES}; mb={}; evidence=collections.Counter()
 initial=.94 if policy in ('buyer_start','buyer_combo94') else .97 if policy=='buyer_combo97' else 1.
 mt['INSTANT']=initial
 for r in ctx.memory.rounds:
  sent={(o['rfq_id'],o['lot_id']):o for o in ctx.memory.sent.get(r['round_id'],[])}
  gt={}; gb={}
  for o in r['my_offers']:
   p=sent.get((o['rfq_id'],o['lot_id']))
   if not p: continue
   gt.setdefault(p['buyer_type'],[]).append(o)
   gb.setdefault((p['buyer'],p['buyer_type']),[]).append(o)
  k=1.5-int(r['round_id'][1:])/ctx.rules['timeline']['rounds']
  for t,rows in gt.items(): mt[t]=min(1.3,max(.85,mt[t]+step(rows,k,policy=='volume')))
  for (b,t),rows in gb.items():
   start=initial if t=='INSTANT' else 1.
   mb[b]=min(1.3,max(.85,mb.get(b,start)+step(rows,k,policy in ('buyer_volume','buyer_combo94','buyer_combo97'))))
   if any(o['status']!='SPEC_MISMATCH' for o in rows): evidence[b]+=1
 free={}
 if ctx.memory.rounds:
  gs={}
  for row in ctx.memory.rounds[-1]['market_summary']:
   a=gs.setdefault(row['buyer'],[0,0]); a[0]+=row['wanted_kg']; a[1]+=row['bought_kg']
  free={b:1-v[1]/max(1,v[0]) for b,v in gs.items()}
 for c in candidates:
  m=mt[c['buyer_type']]
  if policy.startswith('buyer') and c['buyer'] in mb:
   weight=1. if policy=='buyer_pure' else evidence[c['buyer']]/(evidence[c['buyer']]+2.)
   m=weight*mb[c['buyer']]+(1-weight)*m
  c['markup']=m; c['price_per_kg']=round(c['tv']*m,2)
 jitter={'spread0':0.,'spread1':.01,'spread3':.03,'spread8':.08}.get(variant,0.)
 for c in candidates:
  c['_score']=c['tv']*c['markup']*(1+.15*free.get(c['buyer'],0.) if policy in ('market','buyer_market') else 1.)
  if jitter: c['_score']*=1+ctx.rng.uniform(-jitter,jitter)
 candidates.sort(key=lambda c:-c['_score'])
 for i,c in enumerate(candidates): c['candidate']=i
 offers=core.allocate(state,candidates,budget)
 ctx.memory.policy_state['react70']=dict(rng_state=rngstate)
 return offers

def memory(): return SimpleNamespace(rounds=[],sent={},policy_state={},save=lambda:None)

def game(task):
 field,policy,seed=task; cfg=FIELDS[field]
 inputs=json.loads((HERE/'inputs.json').read_text(encoding='utf-8'))
 rules=copy.deepcopy(inputs['rules']); R=cfg.get('rounds',6); rules['timeline']['rounds']=R
 n=cfg.get('n',20); rng=random.Random(seed); noise=cfg.get('noise',0.)
 lots=[]
 for i in range(4):
  actual=dict(defect_pct=round(rng.uniform(.5,16.),2),moisture_pct=round(rng.uniform(10.5,15.),2),screen=rng.randint(12,18))
  sample={**actual,'defect_pct':round(max(.1,actual['defect_pct']+rng.gauss(0,noise)),2),
          'moisture_pct':round(max(8,actual['moisture_pct']+rng.gauss(0,.4*noise)),2)}
  lots.append(dict(lot_id=f'L{i}',kg_total=rng.randint(3,10)*60,kg_available=0,sample=sample,actual=actual))
 for l in lots: l['kg_available']=l['kg_total']
 kinds=['COMMERCIAL','INSTANT']+(['SPECIALTY'] if cfg.get('specialty') else [])
 buyers=[(f'{t}-{j}',t) for t in kinds for j in range(2)]
 means=dict(COMMERCIAL=1.04,INSTANT=.92,SPECIALTY=1.12)
 ceilings={b:(.98 if cfg.get('flat') else means[t])+cfg.get('shift',0)+rng.gauss(0,cfg.get('spread',.025)) for b,t in buyers}
 schedule=[]
 for rnd in range(1,R+1):
  rfqs=[]
  for i in range(8 if not cfg.get('specialty') else 12):
   b,t=rng.choice(buyers)
   spec=inputs['specs'].get(t,dict(max_defect_pct=3.,max_moisture_pct=12.,min_screen=16))
   bags=max(1,round(rng.choice(inputs['sizes'])*cfg.get('demand',1.)*n/20))
   rfqs.append(dict(rfq_id=f'R{rnd}-{i}',buyer=b,buyer_type=t,bags=bags,kg=bags*60,spec=spec,
                    ceiling=ceilings[b]+rng.gauss(0,.012)))
  schedule.append(rfqs)
 actual_tv={l['lot_id']:true_value(rules,l['actual']) for l in lots}
 denominator=sum(l['kg_total']*actual_tv[l['lot_id']] for l in lots)
 unsellable=sum(l['kg_total'] for l in lots if not any(strategy.spec_ok(l['actual'],r['spec']) for rfqs in schedule for r in rfqs))
 teams=[]
 for i in range(n):
  opponent=cfg.get('rivals') or ('react70' if cfg.get('copies') else ('react70' if i%3==0 else 'fixed' if i%3==1 else 'random'))
  teams.append(dict(lots=copy.deepcopy(lots),mem=memory(),revenue=0.,policy=policy if i==0 else opponent,rng=random.Random(seed*1000+i)))
 for rnd,full_rfqs in enumerate(schedule,1):
  rfqs=[{k:v for k,v in r.items() if k!='ceiling'} for r in full_rfqs]
  results=[[] for _ in teams]; alloffers=[]
  for i,team in enumerate(teams):
   public=[{k:v for k,v in l.items() if k!='actual'} for l in team['lots']]
   capacity=math.ceil(sum(l['kg_total'] for l in lots)/60/R*1.5)*60 if cfg.get('cap') else None
   state=dict(round=dict(round_id=f'R{rnd}',number=rnd,of=R,kind='real'),lots=public,rfqs=rfqs,capacity_left_kg=capacity,last_results=None)
   tv=estimate_lots(rules,public)
   ctx=strategy.Context(rules,[],tv,team['rng'],team['mem'],None,99,'react70')
   if team['policy'] in ('fixed','random'):
    cs,budget,_,rngstate=core.prepare(state,ctx)
    team['rng'].shuffle(cs); cs.sort(key=lambda c:-c['tv'])
    for j,c in enumerate(cs):
     mk=1. if team['policy']=='fixed' else team['rng'].uniform(.85,1.12)
     c.update(candidate=j,markup=mk,price_per_kg=round(c['tv']*mk,2))
    offers=core.allocate(state,cs,budget); team['mem'].policy_state['react70']=dict(rng_state=rngstate)
   else: offers=decide(state,ctx,team['policy'])
   lotvol=collections.Counter(); rfqvol=collections.Counter()
   for o in offers:
    assert o['kg']>0 and o['kg']%60==0
    lotvol[o['lot_id']]+=o['kg']; rfqvol[o['rfq_id']]+=o['kg']
   assert capacity is None or sum(o['kg'] for o in offers)<=capacity
   assert all(lotvol[l['lot_id']]<=l['kg_available'] for l in public)
   assert all(rfqvol[r['rfq_id']]<=r['kg'] for r in rfqs)
   assert len({(o['rfq_id'],o['lot_id']) for o in offers})==len(offers)
   meta={r['rfq_id']:r for r in rfqs}
   team['mem'].sent[f'R{rnd}']=[dict(o,buyer=meta[o['rfq_id']]['buyer'],buyer_type=meta[o['rfq_id']]['buyer_type'],spec=meta[o['rfq_id']]['spec']) for o in offers]
   alloffers.append(offers)
  summaries=[]
  for rfq in full_rfqs:
   eligible=[]; submitted=0; soldprices=[]
   for i,offers in enumerate(alloffers):
    for o in offers:
     if o['rfq_id']!=rfq['rfq_id']: continue
     submitted+=1; lot=next(l for l in teams[i]['lots'] if l['lot_id']==o['lot_id'])
     ratio=o['price_per_kg']/actual_tv[o['lot_id']]
     status='SPEC_MISMATCH' if not strategy.spec_ok(lot['actual'],rfq['spec']) else 'ABOVE_LIMIT' if ratio>rfq['ceiling'] else None
     if status: results[i].append(dict(o,status=status,filled_kg=0))
     else: eligible.append((ratio,i,o))
   eligible.sort(key=lambda e:e[0]); remaining=rfq['kg']; cursor=0
   tie_rng=random.Random(seed*10000+rnd*100+int(rfq['rfq_id'].split('-')[1]))
   while cursor<len(eligible):
    end=cursor+1
    while end<len(eligible) and abs(eligible[end][0]-eligible[cursor][0])<1e-12: end+=1
    tied=eligible[cursor:end]; tie_rng.shuffle(tied); fills=[0]*len(tied)
    while remaining>=60 and any(fills[j]<e[2]['kg'] for j,e in enumerate(tied)):
     for j,(_,i,o) in enumerate(tied):
      if remaining>=60 and fills[j]<o['kg']: fills[j]+=60; remaining-=60
    for j,(_,i,o) in enumerate(tied):
     fill=fills[j]; results[i].append(dict(o,status='ACCEPTED' if fill==o['kg'] else 'PARTIAL' if fill else 'OUTBID',filled_kg=fill))
     if fill: soldprices.append((o['price_per_kg'],fill))
    cursor=end
   summaries.append(dict(rfq_id=rfq['rfq_id'],buyer=rfq['buyer'],buyer_type=rfq['buyer_type'],wanted_kg=rfq['kg'],bought_kg=rfq['kg']-remaining,offers=submitted,
                         price_min=min((p for p,k in soldprices),default=None),price_max=max((p for p,k in soldprices),default=None),
                         price_avg=sum(p*k for p,k in soldprices)/sum(k for p,k in soldprices) if soldprices else None))
  for i,team in enumerate(teams):
   for o in results[i]:
    lot=next(l for l in team['lots'] if l['lot_id']==o['lot_id']); lot['kg_available']-=o['filled_kg']
    assert lot['kg_available']>=0
    team['revenue']+=o['filled_kg']*o['price_per_kg']
   team['mem'].rounds.append(dict(round_id=f'R{rnd}',my_offers=results[i],market_summary=summaries))
 scores=[(t['revenue']+.8*sum(l['kg_available']*actual_tv[l['lot_id']] for l in t['lots']))/denominator for t in teams]
 own=scores[0]; better=sum(x>own+1e-12 for x in scores[1:]); equal=sum(abs(x-own)<=1e-12 for x in scores[1:])
 rank=1+better+equal/2 # midrank avoids giving all tied clones top 1
 sold=sum(l['kg_total']-l['kg_available'] for l in teams[0]['lots'])
 statuses=collections.Counter(o['status'] for r in teams[0]['mem'].rounds for o in r['my_offers'])
 return dict(field=field,policy=policy,seed=seed,teams=n,pr=own,rank=rank,rank_best=1+better,rank_worst=1+better+equal,
             sold_kg=sold,structurally_unsellable_kg=unsellable,eligible_kg=sum(l['kg_total'] for l in lots)-unsellable,statuses=dict(statuses))

def summary(rows):
 out={}
 for p in sorted({r['policy'] for r in rows}):
  fs={}
  for f in FIELDS:
   rs=[r for r in rows if r['field']==f and r['policy']==p]
   if not rs: continue
   fs[f]=dict(pr=statistics.mean(r['pr'] for r in rs),rank=statistics.mean(r['rank'] for r in rs),top5=sum(r['rank_worst']<=5 for r in rs)/len(rs),
              eligible_sell_rate=sum(r['sold_kg'] for r in rs)/max(1,sum(r['eligible_kg'] for r in rs)))
  out[p]=dict(fields=fs,mean_rank=statistics.mean(x['rank'] for x in fs.values()),worst_field=max(x['rank'] for x in fs.values()),pr=statistics.mean(x['pr'] for x in fs.values()))
 return out

if __name__=='__main__':
 stage=sys.argv[1] if len(sys.argv)>1 else 'search'
 if not (HERE/'inputs.json').exists(): bootstrap()
 if stage=='search': policies=POLICIES; seeds=range(810000,810010)
 elif stage=='combine': policies=('buyer_start','buyer_volume','buyer_combo94','buyer_combo97'); seeds=range(1010000,1010010)
 elif stage=='final':
  old=json.loads((HERE/'combine.json').read_text())['summary']
  best=min(('buyer_combo94','buyer_combo97'),key=lambda p:old[p]['worst_field'])
  policies=('react70','buyer_start','buyer_volume',best); seeds=range(1110000,1110040)
 elif stage=='spread': policies=('buyer_combo97','spread0','spread1','spread3','spread8'); seeds=range(1210000,1210010)
 elif stage=='confirm':
  old=json.loads((HERE/'spread.json').read_text())['summary']
  best=min(('spread0','spread1','spread3','spread8'),key=lambda p:old[p]['worst_field'])
  policies=('react70','buyer_combo97',best); seeds=range(1310000,1310040)
 else:
  old=json.loads((HERE/'search.json').read_text())['summary']
  candidates=[p for p in old if p!='react70']
  best_mean=min(candidates,key=lambda p:old[p]['mean_rank']); best_worst=min(candidates,key=lambda p:old[p]['worst_field'])
  policies=list(dict.fromkeys(['react70',best_mean,best_worst,'buyer_volume'])); seeds=range(910000,910040)
 fields=FIELDS if stage in ('final','spread','confirm') else BASE_FIELDS
 tasks=[(f,p,s) for f in fields for p in policies for s in seeds]; rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  for r in pool.map(game,tasks,chunksize=4):
   rows.append(r)
   if len(rows)%80==0: print(stage,len(rows),'/',len(tasks),r['field'],flush=True)
 result=dict(stage=stage,policies=policies,summary=summary(rows),rows=rows)
 (HERE/(stage+'.json')).write_text(json.dumps(result,indent=2))
 for p,v in sorted(result['summary'].items(),key=lambda x:x[1]['mean_rank']): print(p,round(v['mean_rank'],3),round(v['worst_field'],3),round(v['pr'],5),flush=True)
