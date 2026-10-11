#!/usr/bin/env bash
# Read-only Chakra launcher inspection and RVOL/run_now unit tests.
# No broker connection, no bot restart, no order and no Discord send.
set -euo pipefail
ROOT=/root/trading/ASJR
PY=/root/trading/venv_new/bin/python
LAUNCH=/root/trading/utils/trading_sudarsan_chakra.py
cd "$ROOT" || exit 2
echo "=== GIT / VERSION ==="
git status --short
git log -1 --format='%h %s'
echo "=== PYTHON COMPILE (no import execution) ==="
"$PY" -m py_compile ASJR_Analyst/Tests/test_asjr_pipeline.py \
 RudraScanner/run_now.py RudraScanner/scan_now.py \
 RudraScanner/premarket_rvol.py RudraScanner/premarket_backfill.py \
 RudraScanner/premarket_diagnostic.py RudraScanner/premarket_live.py \
 RudraScanner/premarket_live_backfill.py RudraScanner/live_round.py
echo "=== TARGETED TESTS ==="
"$PY" -m unittest discover -s RudraScanner/tests -p 'test_premarket*.py' -v
"$PY" -m unittest discover -s RudraScanner/tests -p 'test_run_now.py' -v
echo "=== SAFE NO-BROKER CHECK ==="
if "$PY" RudraScanner/run_now.py --mode standalone --dry-run; then
  echo "PASS: one-shot launch prerequisites"
else
  if tmux has-session -t trading_bot 2>/dev/null; then
    echo "PASS: standalone safety refused because scheduled bot exists"
  else
    echo "ERROR: standalone dry-run failed; inspect launcher/lock"; exit 1
  fi
fi
echo "Dry-run did not connect to IBKR."
echo "=== LAUNCHER PATH ==="
if [[ -f "$LAUNCH" ]]; then
  ls -l "$LAUNCH"
  echo "Relevant launch/call definitions (review before sharing; redact secrets):"
  grep -nE '^(def |class |if __name__)|run_asjr_manual_pipeline|prepare_alert|send_to_discord|EClient|connect\(|clientId|thread|tmux|lock|ibkr_trading_sudarsan_chakra' "$LAUNCH" | head -110 || true
  echo "To share launcher safely: inspect locally with: sed -n '1,240p' $LAUNCH"
  echo "Do NOT paste passwords, tokens, webhook URLs or private account details."
else
  echo "LAUNCHER NOT FOUND at $LAUNCH"
fi
echo "=== PROCESSES (no secret command lines) ==="
pgrep -af 'trading_sudarsan_chakra|trading_bot' | sed -E 's/(token|password|secret|webhook|api_key)=([^ ]+)/\1=[REDACTED]/g' | head -15 || true
echo "=== DONE — no live broker pipeline was launched ==="
