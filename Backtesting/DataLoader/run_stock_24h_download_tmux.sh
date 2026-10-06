#!/usr/bin/env bash
set -u

ASJR_ROOT="${ASJR_ROOT:-/root/trading/ASJR}"
PYTHON_BIN="${PYTHON_BIN:-/root/trading/venv_new/bin/python}"
TMUX_SESSION="${STOCK24_TMUX_SESSION:-stock_24h_download}"

STATE_DIR="$ASJR_ROOT/Backtesting/BacktestData/IBKR/MarketData24h/.state"
LOG_DIR="$ASJR_ROOT/Backtesting/BacktestData/IBKR/MarketData24h/logs"
RUNNING_FILE="$STATE_DIR/high_liquidity_1y_5m.running"
DONE_FILE="$STATE_DIR/high_liquidity_1y_5m.done"
LOG_FILE="$LOG_DIR/high_liquidity_1y_5m.log"

mkdir -p "$STATE_DIR" "$LOG_DIR"

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "STOCK24 | already running | tmux=$TMUX_SESSION"
    echo "Status: tail -f '$LOG_FILE'"
    exit 0
fi

if [[ -f "$DONE_FILE" ]]; then
    echo "STOCK24 | already completed | $DONE_FILE"
    echo "Log: $LOG_FILE"
    exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "STOCK24 | ERROR | python not executable: $PYTHON_BIN" >&2
    exit 1
fi

cd "$ASJR_ROOT" || exit 1

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$RUNNING_FILE"

TICKERS="INTC NVDA AMD AMAT LRCX META MSFT GOOGL GOOG QCOM"

CMD="cd '$ASJR_ROOT'; echo '===== STOCK 24H ONE-TIME DOWNLOAD START =====' >> '$LOG_FILE'; date -u +'%Y-%m-%dT%H:%M:%SZ' >> '$LOG_FILE'; '$PYTHON_BIN' -u IBKR_import.py   --24h   --tickers $TICKERS   --interval 5m   --start 2025-10-02   --end 2026-10-02   --client-id 42   --pacing-sleep 1   --concurrency 3   >> '$LOG_FILE' 2>&1; rc=\$?; echo STOCK24_EXIT=\$rc >> '$LOG_FILE'; if [ \$rc -eq 0 ]; then   date -u +'%Y-%m-%dT%H:%M:%SZ' > '$DONE_FILE'; else   echo 'STOCK24 | FAILED - see errors above' >> '$LOG_FILE'; fi; rm -f '$RUNNING_FILE'; echo '===== STOCK 24H ONE-TIME DOWNLOAD END =====' >> '$LOG_FILE'; exit \$rc"

tmux new-session -d -s "$TMUX_SESSION" "bash -lc \"$CMD\""

echo "STOCK24 | started"
echo "tmux : $TMUX_SESSION"
echo "log  : $LOG_FILE"
echo
echo "Check status:"
echo "  tmux ls"
echo "  tail -f '$LOG_FILE'"
echo
echo "Attach:"
echo "  tmux attach -t '$TMUX_SESSION'"
