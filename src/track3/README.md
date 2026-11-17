# Track 3: coffee market agent

The market bot supports `spread1` (buyer-specific, volume-weighted feedback and
1% RFQ ranking jitter) and `react70` (buyer-type feedback). Both rule modes run
without LLM calls. Existing `agent.py` and `app.py` remain the separate MQTT
sensor integration; this upload does not wire their readings into the market bot.

## Run from this directory (PowerShell, Python 3.10+)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: MARKET_URL = server root (without /trade), TEAM_KEY = your key.
# Default example: USE_LLM=0, STRATEGY_MODE=spread1.
.\.venv\Scripts\python.exe -u main.py --forever
```

Running main.py submits appraisals and offers to the configured market. Stop any
other bot for the same team first. Omit `--forever` to exit after the game closes.
Use the virtual environment interpreter: main.py currently imports the LLM
module at startup, so its dependencies are needed even for rule-only mode.
Never commit `.env` or real keys. Live `logs/`, virtual environments and backups
are excluded from this upload.

## Offline verification

```powershell
.\.venv\Scripts\python.exe -B -m unittest test_react70
.\.venv\Scripts\python.exe -B test_spread1.py
```

`test_spread1.py` compares production decisions/results against the lab formula
and checks JSON restart continuity. It does not contact the market.

## Files and evidence

- `Conclusion.txt`: Thai explanation of both policies, all 13 lab fields,
  experimental opponents, measured results, limitations and rules.
- `RUN_SPREAD1.md`: running and switching back to react70.
- `STARTER_README.md`, `คู่มือ-API.md`: upstream starter guidance and API reference.
- `lab_experiments/`: frozen baseline, inputs, simulator, results and report.
  These are synthetic markets, not recovered organizer server code.
  Local paths in historical reports refer to the original experiment machine.
  The report's "production unchanged" statement describes the offline experiment
  before spread1 was installed, not the present integration state.

Latest held-out simulation: spread1 average PR rank 3.00 across 13 fields,
Top 5 in 445/520 games, versus react70 8.55 and 186/520. Fields mix 20 and
56 teams. These are not official live rankings or a guarantee of competition rank.
Historical live sandbox results summarized in Conclusion.txt lack complete
leaderboard/reveal snapshots; no retrospective official rank is claimed.

The market client and starter originate from
https://github.com/khthana/Coffee-TESA-starter with local strategy modifications.
