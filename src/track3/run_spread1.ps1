# Explicit overrides avoid inherited environment settings selecting an old policy.
$env:STRATEGY_MODE = 'spread1'
$env:USE_LLM = '0'
Push-Location $PSScriptRoot
try {
    & "$PSScriptRoot\.venv\Scripts\python.exe" -u main.py @args
} finally {
    Pop-Location
}
