# Test spread1 without an LLM

Stop the previously running bot with Ctrl+C before starting this one. Prefer
the start of a fresh game when comparing strategies: changing mid-game carries
earlier offers and feedback forward and is not a clean comparison.

PowerShell:

```powershell
cd <repository>\src\track3
.\run_spread1.ps1 --forever
```

If PowerShell prevents running scripts, use these commands instead:

```powershell
$env:STRATEGY_MODE='spread1'
$env:USE_LLM='0'
.\.venv\Scripts\python.exe -u main.py --forever
```

The runner uses the existing MARKET_URL and TEAM_KEY from .env. It sends real
offers to that configured market when you run it. Logs show source=spread1_rules
and pricing_mode=spread1. Omit --forever to stop after the game closes.

To switch back, stop the bot and run:

```powershell
$env:STRATEGY_MODE='react70'
$env:USE_LLM='0'
.\.venv\Scripts\python.exe -u main.py --forever
```

spread1 uses buyer-volume feedback, type priors, Instant initial markup .97,
and independent RFQ ordering with 1% ranking jitter (not price jitter).
Spec blacklist, pace 2, half-lot-budget splitting and volume guards remain.
Both random streams persist in memory separately from react70. It does not call
an LLM, even if a client object is supplied. Existing API credentials are unchanged.

Offline verification: `.\.venv\Scripts\python.exe -B test_spread1.py`.
Simulation evidence and limitations: lab_experiments/REPORT.md. Simulation
rankings are not guaranteed live rankings. Record whole-game PR and standings
before comparing against react70; avoid attributing structurally unsellable
stock to pricing failures.
