#!/usr/bin/env bash
ASJR_ROOT="${ASJR_ROOT:-/root/trading/ASJR}"
TMUX_SESSION="${STOCK24_TMUX_SESSION:-stock_24h_download}"
LOG_FILE="$ASJR_ROOT/Backtesting/BacktestData/IBKR/MarketData24h/logs/high_liquidity_1y_5m.log"
DONE_FILE="$ASJR_ROOT/Backtesting/BacktestData/IBKR/MarketData24h/.state/high_liquidity_1y_5m.done"

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "STOCK24 | RUNNING | tmux=$TMUX_SESSION"
elif [[ -f "$DONE_FILE" ]]; then
    echo "STOCK24 | COMPLETE"
else
    echo "STOCK24 | NOT RUNNING"
fi

echo
echo "Latest log:"
if [[ -f "$LOG_FILE" ]]; then
    tail -n 40 "$LOG_FILE"
else
    echo "No log yet: $LOG_FILE"
fi
