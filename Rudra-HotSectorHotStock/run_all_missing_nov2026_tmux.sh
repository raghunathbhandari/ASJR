#!/usr/bin/env bash
# ASJR | one-command, disconnect-safe November 2026 missing-stock download.
# No IBKR orders. Does not git pull/reset the live working tree.
set -Eeuo pipefail

ROOT="/root/trading/ASJR"
PY="/root/trading/venv_new/bin/python"
SESSION="asjr_nov2026_all"
LOGDIR="/root/trading/ASJR_research_logs/hot_sector"
SELF="$(readlink -f "$0")"
export TZ="Europe/London"
WEB="/tmp/asjr_nov2026_web_shortlists.py"
IBKR="/tmp/asjr_nov2026_ibkr_top10.py"

if [[ ! -d "$ROOT/.git" || ! -x "$PY" ]]; then
  echo "ERROR: VPS ASJR repository or venv_new Python not found."
  exit 2
fi

mkdir -p "$LOGDIR"
LOG="$LOGDIR/nov2026_all_stock_days.log"

if [[ "$#" -eq 0 ]]; then
  if ! command -v tmux >/dev/null 2>&1; then
    echo "ERROR: tmux is unavailable."
    exit 2
  fi
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "ALREADY RUNNING | tmux session=$SESSION"
    echo "MONITOR | tail -f '$LOG'"
    echo "ATTACH  | tmux attach -t '$SESSION'"
    exit 0
  fi
  echo "LAUNCH | $(date '+%Y-%m-%d %H:%M:%S %Z')"
  tmux new-session -d -s "$SESSION" "bash '$SELF' --worker >> '$LOG' 2>&1"
  echo "STARTED | tmux session=$SESSION | survives SSH disconnect"
  echo "LOG     | $LOG"
  echo "MONITOR | tail -f '$LOG'"
  echo "ATTACH  | tmux attach -t '$SESSION'"
  exit 0
fi
if [[ "$1" != "--worker" ]]; then
  echo "ERROR: Unknown worker argument."
  exit 2
fi

# Lock independent of tmux session name.
exec 9>"$LOGDIR/nov2026_stock_download.lock"
if ! flock -n 9; then
  echo "LOCKED | Another ASJR November stock-download pipeline holds the lock."
  exit 3
fi

cd "$ROOT"
echo "================================================================================"
echo "START | $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "JOB   | web shortlists for missing November dates, then IBKR 5-minute stock days"
echo "REPO  | origin/main only; no git checkout, pull, reset, or bot restarts"
echo "================================================================================"

echo "STAGE 1 | Refresh GitHub main reference"
git fetch -q origin main:refs/remotes/origin/main
git show origin/main:Rudra-HotSectorHotStock/build_november_web_shortlists.py > "$WEB"
git show origin/main:Rudra-HotSectorHotStock/download_daywise_top10_ibkr_5min.py > "$IBKR"
echo "RESEARCH SCRIPTS | fetched"

# Only the website scraper needs BeautifulSoup. Never pip-install
# into the trading bot's Python environment; use an isolated target.
if ! "$PY" -c "import bs4" >/dev/null 2>&1; then
  VENDOR="$LOGDIR/python_web_research_vendor"
  if [[ ! -d "$VENDOR/bs4" ]]; then
    echo "DEPENDENCY | Installing beautifulsoup4 to isolated $VENDOR"
    "$PY" -m pip install --disable-pip-version-check --quiet \
      --target "$VENDOR" beautifulsoup4
  fi
  export PYTHONPATH="$VENDOR"
  "$PY" -c "import bs4;print('WEB PARSER | BeautifulSoup ready')"
fi

echo "STAGE 2 | Build missing day-wise web sector stock top-10 lists"
set +e
"$PY" -u "$WEB"
WEB_RESULT=$?
set -e
echo "WEB STAGE EXIT | $WEB_RESULT (nonzero may mean some dates remain unresolved)"

echo "STAGE 3 | Download every missing IBKR 5m stock-day"
git fetch -q origin main:refs/remotes/origin/main
set +e
"$PY" -u "$IBKR" --limit 0
IBKR_RESULT=$?
set -e
echo "IBKR STAGE EXIT | $IBKR_RESULT"
echo "FINISH | $(date '+%Y-%m-%d %H:%M:%S %Z')"
if [[ $WEB_RESULT -eq 0 && $IBKR_RESULT -eq 0 ]]; then
  echo "PIPELINE COMPLETED | Re-run to pick up any future missing lists."
  exit 0
fi
echo "PIPELINE NEEDS REVIEW | Read PENDING / DOWNLOAD FAILED messages above."
echo "Safe to rerun: completed stock-days and researched dates are reused."
exit 1
