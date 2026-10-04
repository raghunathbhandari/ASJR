"""Replay a frozen research configuration and export reusable BUY signals.

The same signal_mask produces chart markers and the backtest entries. This
does not place orders. September-tuned configurations need independent
validation before use as a trading system.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from research_mu import indicators, signal_mask, simulate, stats


def generate_filtered_signals(bars, config):
    data = indicators(bars)
    data['BuySignal'] = signal_mask(data, config)
    data['ResearchStop'] = (
        data.Low - .01 if config['stop']=='signal' else
        data.SwingLow5 - .01 if config['stop']=='swing5' else
        pd.concat([data.SwingLow5-.01,data.Close-data.ATR],axis=1).min(axis=1)
    )
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--start-date',required=True)
    parser.add_argument('--end-date',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    if 'selected_config' in config: config=config['selected_config']
    data=generate_filtered_signals(pd.read_csv(args.csv),config)
    trades=simulate(data,data.BuySignal.to_numpy(),config,args.start_date,args.end_date)
    args.output.mkdir(parents=True,exist_ok=True)
    cols=['Datetime','CandleTimeUK','Open','High','Low','Close','Volume','EMA9','VWAP','ATR','ADX','RSI','Trend5','TrendMovePct5','EMASlopeATR','Efficiency','BuySignal','ResearchStop']
    data.loc[data.Session.between(args.start_date,args.end_date)&data.RTH,cols].to_csv(args.output/'signals.csv',index=False)
    trades.to_csv(args.output/'trades.csv',index=False)
    print(json.dumps(stats(trades),indent=2))
    print(trades.to_string(index=False))


if __name__=='__main__': main()
