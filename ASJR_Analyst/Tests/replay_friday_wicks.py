"""Replay saved Friday wicks without changing live logs or alert state."""
import argparse
import ast
import importlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ASJR_Analyst'))
from Utils import asjr_alerts as alerts

FRIDAY_COMMIT = 'eea41cd8c9b83477b2dd2bdcce68877910137c1d'
CSV_PATH = 'ASJR_Analyst/DataLake/2026-10-02/raw/intraday_5m.csv'


def resolve_sender(caller_path):
    """Read the actual SN import; never import or start the trading bot."""
    caller_path = Path(caller_path)
    source = ast.parse(caller_path.read_text())
    sys.path.insert(0, str(ROOT.parent))
    sys.path.insert(0, str(caller_path.parent))
    for node in source.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == 'SN':
                    module = importlib.import_module(alias.name)
                    return module.send_to_discord
        if isinstance(node, ast.ImportFrom) and not node.level:
            for alias in node.names:
                if alias.asname == 'SN':
                    parent = importlib.import_module(node.module)
                    module = getattr(parent, alias.name, None)
                    if module is None:
                        module = importlib.import_module(node.module + '.' + alias.name)
                    return module.send_to_discord
    raise RuntimeError('Cannot resolve the SN import in the caller. No alerts sent; inspect its import line.')


def replay(csv_text, workspace):
    from io import StringIO
    frame = pd.read_csv(StringIO(csv_text)).rename(columns={
        'Ticker':'ticker', 'Date':'datetime', 'Open':'open', 'High':'high',
        'Low':'low', 'Close':'close', 'Volume':'volume',
    })
    frame['datetime'] = pd.to_datetime(frame['datetime'], utc=True)
    state = Path(workspace) / 'state.json'
    batch = Path(workspace) / 'batch.json'
    alerts._write_json_atomic(state, alerts._new_state('2026-10-02', seed_latest=False))
    events = alerts.build_wick_alerts(frame, trade_date='2026-10-02',
        now='2026-10-02 20:00:00Z', state_file=state)
    messages = []
    remaining = events[:]
    while remaining:
        message = alerts.prepare_alert({'alert_data':remaining}, state_file=state, batch_file=batch)
        if not message:
            raise RuntimeError('An event cannot fit in a Discord batch.')
        messages.append('FRIDAY REPLAY | 2026-10-02 | historical test\n' + message)
        keys = set(json.loads(batch.read_text())['event_keys'])
        remaining = [e for e in remaining if alerts._event_key(e) not in keys]
    return events, messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send', action='store_true', help='Send historical test batches to Discord.')
    parser.add_argument('--caller', default='/root/trading/utils/trading_sudarsan_chakra.py')
    args = parser.parse_args()
    # The last verified nonempty Friday snapshot; do not fetch fresh IBKR data.
    saved = subprocess.run(['git','show',FRIDAY_COMMIT + ':' + CSV_PATH],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory(prefix='asjr_friday_replay_') as workspace:
        events, messages = replay(saved, workspace)
    print(f'Friday replay: {len(events)} wick signals / {len(messages)} Discord batches', flush=True)
    for ticker in ('INTC','MSFT'):
        subset = [e for e in events if e['ticker'] == ticker]
        times = [pd.Timestamp(e['bar_time_et'].replace(' ET','')).tz_localize(alerts.ET).tz_convert(alerts.UK).strftime('%H:%M %Z') for e in subset]
        print(ticker + ': ' + ', '.join(times), flush=True)
    if not args.send:
        print('Preview only. Add --send to deliver Friday test alerts.')
        return
    sender = resolve_sender(args.caller)
    if not callable(sender):
        raise RuntimeError('Resolved Discord sender is not callable. No alerts sent.')
    unknown = 0
    for idx, message in enumerate(messages, 1):
        result = sender(message)
        if result is False:
            raise RuntimeError(f'Discord helper reported failure at batch {idx}; stopped.')
        if result is not True:
            unknown += 1
        print(f'Discord helper called: batch {idx}/{len(messages)}', flush=True)
        time.sleep(1)
    if unknown:
        print('Helper returned no success flag for some batches; check Discord to confirm delivery.')
    print('Replay finished. Live alert state and logs were not changed.')


if __name__ == '__main__':
    main()
