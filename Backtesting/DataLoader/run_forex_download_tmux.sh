#!/usr/bin/env bash
set -u

ASJR_ROOT="${ASJR_ROOT:-/root/trading/ASJR}"
PYTHON_BIN="${PYTHON_BIN:-/root/trading/venv_new/bin/python}"
TMUX_SESSION="${FOREX_TMUX_SESSION:-forex_download}"
STATE_DIR="$ASJR_ROOT/Backtesting/BacktestData/IBKR/Forex/.state"
LOG_DIR="$ASJR_ROOT/Backtesting/BacktestData/IBKR/Forex/logs"
DONE_FILE="$STATE_DIR/EURUSD_1y_1d_4h_1h.done"
RUNNING_FILE="$STATE_DIR/EURUSD_1y_1d_4h_1h.running"
LOG_FILE="$LOG_DIR/EURUSD_1y_download.log"
DOWNLOADER="$ASJR_ROOT/Backtesting/DataLoader/forex_historical_downloader.py"

mkdir -p "$STATE_DIR" "$LOG_DIR"

if [[ -f "$DONE_FILE" ]]; then
    echo "FOREX_DOWNLOAD | already complete | $DONE_FILE"
    exit 0
fi

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "FOREX_DOWNLOAD | already running | tmux=$TMUX_SESSION"
    exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "FOREX_DOWNLOAD | ERROR | python not executable: $PYTHON_BIN" >&2
    exit 1
fi

if [[ ! -f "$DOWNLOADER" ]]; then
    echo "FOREX_DOWNLOAD | ERROR | downloader missing: $DOWNLOADER" >&2
    exit 1
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUNNING_FILE"

CMD="cd '$ASJR_ROOT' && \
'$PYTHON_BIN' -u '$DOWNLOADER' --pair EURUSD --years 1 --intervals 1d,4h,1h --client-id 41 \
>> '$LOG_FILE' 2>&1; \
rc=\$?; \
if [ \$rc -eq 0 ]; then \
  date -u +'%Y-%m-%dT%H:%M:%SZ' > '$DONE_FILE'; \
fi; \
rm -f '$RUNNING_FILE'; \
echo FOREX_DOWNLOAD_EXIT=\$rc >> '$LOG_FILE'; \
exit \$rc"

tmux new-session -d -s "$TMUX_SESSION" "bash -lc \"$CMD\""

echo "FOREX_DOWNLOAD | started | tmux=$TMUX_SESSION | log=$LOG_FILE"
exit 0
