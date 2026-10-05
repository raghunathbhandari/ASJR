"""Kronos-base forecast veto for existing MU BUY signals; research only.

No future OHLC input, no volume input, no training on trade outcomes.
Requires the official shiyu-coder/Kronos checkout and its dependencies.
Example: python kronos_signal_review.py --features features.pkl --kronos-root /path/Kronos
Features must come from research_mu.indicators on chronological 24h OHLCV.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from fresh_line_angle_detector import generate_signals

MODEL_REVISION = '2b554741eca47781b64468546e77fef3e85130e6'
TOKENIZER_REVISION = '0e0117387f39004a9016484a186a908917e22426'


def timed_signals(data):
    signals = generate_signals(data)
    signals['Signal'] = False
    qualifying = generate_signals(data).Signal
    for _, day in signals[signals.RTH].groupby('Session', sort=True):
        previous = None
        armed = None
        used = False
        for step, (index, bar) in enumerate(day.iterrows()):
            if previous is not None and previous.Close <= previous.EMA9 and bar.Close > bar.EMA9:
                armed, used = step, False
            if bar.Close <= bar.EMA9 or (armed is not None and step - armed > 2):
                armed = None
            if armed is not None and not used and qualifying.loc[index]:
                signals.loc[index, 'Signal'] = True
                used = True
            previous = bar
    return signals


def replay(signals, dates):
    records = []
    for date in dates:
        day = signals[signals.Session.eq(date) & signals.RTH]
        position = None
        for step, (index, bar) in enumerate(day.iterrows()):
            last = step == len(day) - 1
            if position is not None:
                if bar.Close <= bar.EMA9 * 1.0001 or last:
                    records.append({**position, 'ExitTime': str(bar.CandleTimeUK),
                                    'Exit': float(bar.Close),
                                    'GainPct': (bar.Close / position['Entry'] - 1) * 100})
                    position = None
                continue
            if bar.Signal and not last:
                position = {'Index': index, 'Date': date, 'EntryTime': str(bar.CandleTimeUK),
                            'Entry': float(bar.Close)}
    return pd.DataFrame(records, columns=['Index','Date','EntryTime','Entry','ExitTime','Exit','GainPct'])


def forecast_gate(data, position, predictor, torch, samples=5, context=128, horizon=3):
    # Slice by position, never by future timestamps or future values.
    history = data.iloc[max(0, position-context+1):position+1]
    if len(history) < 32:
        return {'Keep': False, 'Reason': 'insufficient history'}
    columns = ['Open', 'High', 'Low', 'Close']
    frame = history[columns].rename(columns=str.lower).reset_index(drop=True)
    timestamps = history.Datetime.dt.tz_convert('America/New_York').dt.tz_localize(None).reset_index(drop=True)
    future = pd.Series(pd.date_range(timestamps.iloc[-1]+pd.Timedelta(minutes=5), periods=horizon, freq='5min'))
    current = float(history.Close.iloc[-1])
    ema_start = float(history.EMA9.iloc[-1])
    terminal, passing = [], []
    for sample in range(samples):
        seed = 20261005 + position * samples + sample
        torch.manual_seed(seed)
        np.random.seed(seed % (2**32))
        prediction = predictor.predict(df=frame, x_timestamp=timestamps,
                                       y_timestamp=future, pred_len=horizon,
                                       T=1.0, top_p=0.9, sample_count=1, verbose=False)
        closes = prediction.close.to_numpy(dtype=float)
        if len(closes) != horizon or not np.isfinite(closes).all():
            raise ValueError('Invalid model forecast; do not silently accept trade')
        ema = ema_start
        stays_above = True
        for close in closes:
            ema = .2 * close + .8 * ema
            stays_above &= close > ema * 1.0001
        gain = (closes[-1] / current - 1) * 100
        terminal.append(gain)
        passing.append(gain > .10 and stays_above)
    return {'Keep': bool(np.mean(passing) >= .60), 'Reason': 'forecast vote',
            'ForecastVote': float(np.mean(passing)),
            'MedianForecastPct': float(np.median(terminal)),
            'InputEndUTC': str(history.Datetime.iloc[-1]), 'ContextBars': len(history)}


def candle_features(bar):
    """Describe signal-candle anatomy, without imposing extra entry filters."""
    span = float(bar.High-bar.Low)
    return {'BodyPct': abs(float(bar.Close-bar.Open))/bar.Close*100,
            'UpperWickPct': max(0., float(bar.High-max(bar.Open,bar.Close)))/bar.Close*100,
            'LowerWickPct': max(0., float(min(bar.Open,bar.Close)-bar.Low))/bar.Close*100,
            'CloseLocation': float((bar.Close-bar.Low)/span) if span>0 else None,
            'BullishCandle': bool(bar.Close>bar.Open)}


def stats(trades):
    returns = trades.GainPct
    return {'Trades': len(trades), 'Good': int((returns > 0).sum()),
            'Bad': int((returns < 0).sum()),
            'SuccessPct': float((returns > 0).mean()*100) if len(trades) else None,
            'GrossCompoundPct': float(((1+returns/100).prod()-1)*100),
            'IllustrativeNetPct': float(((1+returns/100-.001).prod()-1)*100)}


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--features', help='Trusted locally generated indicator pickle')
    source.add_argument('--csv', help='24h chronological 5-minute OHLCV CSV')
    parser.add_argument('--kronos-root', required=True)
    parser.add_argument('--output', default='kronos_review')
    parser.add_argument('--month', default='2026-09')
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    if args.csv:
        from research_mu import indicators
        data = indicators(pd.read_csv(args.csv)).reset_index(drop=True)
    else:
        data = pd.read_pickle(args.features).reset_index(drop=True)
    if not data.Datetime.is_monotonic_increasing or data.Datetime.duplicated().any():
        raise ValueError('Features must be chronological and timestamp-unique')
    signals = timed_signals(data)
    dates = sorted(signals.loc[signals.RTH & signals.Session.str.startswith(args.month), 'Session'].unique())
    baseline = replay(signals, dates)
    sys.path.insert(0, args.kronos_root)
    import torch
    from model import Kronos, KronosTokenizer, KronosPredictor
    torch.set_num_threads(2)
    tokenizer = KronosTokenizer.from_pretrained('NeoQuasar/Kronos-Tokenizer-base', revision=TOKENIZER_REVISION)
    model = Kronos.from_pretrained('NeoQuasar/Kronos-base', revision=MODEL_REVISION)
    model.eval()
    tokenizer.eval()
    predictor = KronosPredictor(model, tokenizer, device=args.device, max_context=512)
    gates = []
    for count, trade in baseline.iterrows():
        result = forecast_gate(data, int(trade.Index), predictor, torch)
        gates.append({**trade.to_dict(), **candle_features(data.iloc[int(trade.Index)]), **result})
        print(f"{count+1}/{len(baseline)} {trade.EntryTime} keep={result['Keep']}", flush=True)
    review = pd.DataFrame(gates)
    # Fixed original trade points: rejected trades do not create replacement entries.
    kept = review[review.Keep] if len(review) else baseline.iloc[:0]
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    review.to_csv(output/'signal_review.csv', index=False)
    summary = {'Baseline': stats(baseline), 'KronosGate': stats(kept),
               'RemovedGood': int(((review.GainPct>0)&~review.Keep).sum()) if len(review) else 0,
               'RemovedBad': int(((review.GainPct<0)&~review.Keep).sum()) if len(review) else 0,
               'ModelRevision': MODEL_REVISION, 'TokenizerRevision': TOKENIZER_REVISION,
               'Method': '128 past 24h OHLC bars; 5 paths; next 3 bars; >=3 paths terminal >0.10% and above projected EMA9; no volume',
               'Limitations': 'Fixed baseline signal veto; sample frequency is not calibrated probability; provisional VWAP; signal-close fills; no untouched holdout'}
    (output/'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
