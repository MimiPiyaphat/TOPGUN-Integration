"""Preview the prompt; --call tests the configured LLM without any market writes."""
import argparse
import json
import os
import time
from pathlib import Path
from llm import LLM
from main import load_env
from test_react70 import fixture
import strategy

def make_llm(env_path):
    if not Path(env_path).is_file():
        raise FileNotFoundError(f'Configuration not found: {env_path}; pass --env explicitly.')
    load_env(Path(env_path))
    return LLM(os.environ.get('LLM_BASE_URL','http://localhost:11434/v1'),
               os.environ.get('LLM_MODEL','qwen3.5:9b'), os.environ.get('LLM_API_KEY','none'),
               timeout=float(os.environ.get('LLM_TIMEOUT','45')),
               thinking=os.environ.get('LLM_THINKING','0')=='1',
               temperature=float(os.environ.get('LLM_TEMPERATURE','.2')),
               max_tokens=int(os.environ.get('LLM_MAX_TOKENS','1500')))

class Recorder:
    def __init__(self, inner=None): self.inner=inner; self.calls=[]
    def ask_json(self, system, user, schema, timeout):
        started=time.monotonic()
        answer=self.inner.ask_json(system,user,schema,timeout=timeout) if self.inner else {'offers':[],'reason':'Preview only; use rules.'}
        self.calls.append(dict(system=system,input=json.loads(user),schema=schema,response=answer,
                               seconds=time.monotonic()-started,
                               error=getattr(self.inner,'last_error',None)))
        return answer

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--call',action='store_true')
    p.add_argument('--env',default='.env'); args=p.parse_args()
    recorder=Recorder(make_llm(args.env) if args.call else None)
    state,ctx=fixture(); ctx.llm=recorder
    offers,source=strategy.decide(state,ctx)
    result=dict(real_llm=args.call,source=source,offers=offers,notes=ctx.notes,calls=recorder.calls)
    destination=Path('qwen_smoke_result.json' if args.call else 'qwen_prompt_preview.json')
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(real_llm=args.call,source=source,offers=len(offers),artifact=str(destination))))
    if args.call and (not recorder.calls or recorder.calls[-1]['response'] is None
                      or any('fallback:' in n for n in ctx.notes)):
        raise SystemExit('LLM not ready; rule fallback worked. Inspect qwen_smoke_result.json.')
