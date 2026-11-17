"""Offline parity, restart and routing checks. Never connects to the market."""
import copy
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import strategy
import spread1

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / 'lab_experiments'))
import experiment as lab


def main():
    original = lab.decide
    tasks = [(field, 'spread1', seed) for field in lab.FIELDS for seed in (1410000, 1410001)]
    expected = [lab.game(task) for task in tasks]
    restart_checks = 0

    def production(state, ctx, policy):
        nonlocal restart_checks
        if policy != 'spread1':
            return original(state, ctx, policy)
        ctx.pricing_mode = 'spread1'
        # Emulate JSON disk reload and a new process RNG before this decision.
        restored = copy.copy(ctx)
        restored.memory = SimpleNamespace(
            **json.loads(json.dumps(dict(rounds=ctx.memory.rounds, sent=ctx.memory.sent,
                                        policy_state=ctx.memory.policy_state))), save=lambda: None)
        restored.rng = random.Random(999)
        offers, source = strategy.decide(state, ctx)
        assert source == 'spread1_rules'
        if restored.memory.policy_state.get('spread1'):
            assert strategy.decide(state, restored)[0] == offers, 'restart changes decision'
            restart_checks += 1
        return offers

    lab.decide = production
    actual = [lab.game(task) for task in tasks]
    assert actual == expected, 'production differs from lab spread1'
    assert spread1._step([dict(status='SPEC_MISMATCH', kg=60, filled_kg=0)], 1, True) == 0
    print(f'PASS: exact lab parity for {len(tasks)} games across {len(lab.FIELDS)} fields; '
          f'{restart_checks} JSON restart checks; capacity/stock/RFQ assertions in every round')


if __name__ == '__main__':
    main()
