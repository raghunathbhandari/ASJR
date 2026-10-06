#!/usr/bin/env bash
set -u

ASJR_ROOT="${ASJR_ROOT:-/root/trading/ASJR}"
PYTHON_BIN="${PYTHON_BIN:-/root/trading/venv_new/bin/python}"
TMUX_SESSION="${NQ_TMUX_SESSION:-nq_download}"
STATE_DIR="$ASJR_ROOT/Backtesting/BacktestData/OpenSource/NQ/.state"
LOG_DIR="$ASJR_ROOT/Backtesting/BacktestData/OpenSource/NQ/logs"
DONE_FILE="$STATE_DIR/NQ_yfinance.done"
RUNNING_FILE="$STATE_DIR/NQ_yfinance.running"
LOG_FILE="$LOG_DIR/NQ_yfinance_download.log"
DOWNLOADER="$ASJR_ROOT/Backtesting/DataLoader/nq_yfinance_downloader.py"

mkdir -p "$STATE_DIR" "$LOG_DIR"

if [[ -f "$DONE_FILE" ]]; then
    echo "NQ_DOWNLOAD | already complete | $DONE_FILE"
    exit 0
fi

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "NQ_DOWNLOAD | already running | tmux=$TMUX_SESSION"
    exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "NQ_DOWNLOAD | ERROR | python not executable: $PYTHON_BIN" >&2
    exit 1
fi

if [[ ! -f "$DOWNLOADER" ]]; then
    echo "NQ_DOWNLOAD | ERROR | downloader missing: $DOWNLOADER" >&2
    exit 1
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUNNING_FILE"

CMD="cd '$ASJR_ROOT'; echo '===== NQ OPEN-SOURCE DOWNLOAD START =====' >> '$LOG_FILE'; date -u +'%Y-%m-%dT%H:%M:%SZ' >> '$LOG_FILE'; '$PYTHON_BIN' -u '$DOWNLOADER' >> '$LOG_FILE' 2>&1; rc=\$?; echo NQ_DOWNLOAD_EXIT=\$rc >> '$LOG_FILE'; if [ \$rc -eq 0 ]; then   date -u +'%Y-%m-%dT%H:%M:%SZ' > '$DONE_FILE'; else   echo 'NQ_DOWNLOAD | FAILED - see errors above' >> '$LOG_FILE'; fi; rm -f '$RUNNING_FILE'; echo '===== NQ OPEN-SOURCE DOWNLOAD END =====' >> '$LOG_FILE'; GIT_OPS_LOG='$STATE_DIR/git_push.log'; git add Backtesting/BacktestData/OpenSource/NQ Backtesting/DataLoader/nq_yfinance_downloader.py Backtesting/DataLoader/run_nq_download_tmux.sh > \"\$GIT_OPS_LOG\" 2>&1; if ! git diff --cached --quiet; then   git commit -m 'Add open-source NQ historical data' >> \"\$GIT_OPS_LOG\" 2>&1;   git pull --rebase origin main >> \"\$GIT_OPS_LOG\" 2>&1;   git push origin main >> \"\$GIT_OPS_LOG\" 2>&1; else   echo 'NQ_GIT | no changes to commit' >> \"\$GIT_OPS_LOG\"; fi; exit \$rc"

tmux new-session -d -s "$TMUX_SESSION" "bash -lc \"$CMD\""

echo "NQ_DOWNLOAD | started | tmux=$TMUX_SESSION | log=$LOG_FILE"
exit 0
