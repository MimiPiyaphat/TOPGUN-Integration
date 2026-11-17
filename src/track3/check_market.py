"""Read market configuration/state and preview offers. Never posts to the API."""
import json
import os
import random
from pathlib import Path
from main import load_env,HERE
from market import Market
from memory import Memory
from appraisal import estimate_lots
import strategy

if __name__=='__main__':
    load_env(HERE/'.env')
    api=Market(os.environ['MARKET_URL'],os.environ['TEAM_KEY'],timeout=15)
    calendar=api.calendar(); state=api.state()
    directory=HERE/'logs'; directory.mkdir(exist_ok=True)
    (directory/'market_snapshot.json').write_text(json.dumps(dict(calendar=calendar,state=state),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(market=state.get('market'),phase=state.get('phase'),paused=state.get('paused'),
                         round=state.get('round'),seconds_left=state.get('seconds_left'),
                         lots=len(state.get('lots',[])),rfqs=len(state.get('rfqs',[])),
                         capacity_left_kg=state.get('capacity_left_kg'),
                         appraisal_submitted=state.get('appraisal_submitted'),
                         open_offers=len(state.get('my_open_offers',[]))),ensure_ascii=True))
    class PreviewMemory(Memory):
        def save(self): pass
    # Preview starts fresh; main.py uses persisted game-specific feedback.
    memory=PreviewMemory(directory/'preview-unused.json')
    tv=estimate_lots(calendar['rules'],state['lots'])
    ctx=strategy.Context(calendar['rules'],calendar['calendar'],tv,random.Random(11),memory,None,0,'react70')
    if state.get('rfqs'):
        offers,source=strategy.decide(state,ctx)
        print(json.dumps(dict(preview_only=True,source=source,offers=offers),ensure_ascii=True))
