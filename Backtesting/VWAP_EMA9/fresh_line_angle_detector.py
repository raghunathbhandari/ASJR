"""Fresh price/EMA9/VWAP experiment. No volume or oscillator entry filters.

ATR14 is retained ONLY as the deterministic scale of the user-approved chart
angles. Five completed points = displacement from four intervals earlier.
Entries assume signal-close fills; exit only on later close below EMA9 or RTH end.
"""
import numpy as np
import pandas as pd
from ema_cross_area_detector import normalized_angles


def generate_signals(data):
    angles = normalized_angles(data, angle_bars=4)
    change5 = (data.Close / data.Close.shift(4) - 1) * 100
    mask = (data.RTH & (data.Close > data.EMA9) & (data.Close > data.VWAP)
            & angles.PriceAngle.between(15, 65)
            & angles.EMA9Angle.between(15, 65) & change5.gt(.20))
    out = data[['Datetime', 'CandleTimeUK', 'Session', 'RTH', 'Close', 'EMA9', 'VWAP']].copy()
    out = out.join(angles)
    out['Change5Pct'] = change5.where(angles.PriceAngle.notna())
    out['Signal'] = mask.fillna(False)
    return out


def replay(signals, dates):
    """Chronological replay, no overlapping positions or signal-bar exits."""
    records = []
    for date in dates:
        day = signals[signals.Session.eq(date) & signals.RTH].reset_index(drop=True)
        position = None
        for i, bar in day.iterrows():
            last = i == len(day)-1
            if position is not None:
                if bar.Close < bar.EMA9 or last:
                    gain = (bar.Close/position['Entry']-1)*100
                    records.append(dict(**position, ExitCandleUK=str(bar.CandleTimeUK),
                                        Exit=bar.Close, Reason='EMA9 exit' if bar.Close<bar.EMA9 else 'RTH end',
                                        GainPct=gain, Status='Good' if gain>0 else 'Bad' if gain<0 else 'Flat'))
                    position = None
                continue
            if bar.Signal and not last:
                position = dict(Date=date, CandleTimeUK=str(bar.CandleTimeUK), Entry=bar.Close,
                                PriceAngle=bar.PriceAngle, EMA9Angle=bar.EMA9Angle, Change5Pct=bar.Change5Pct)
    return pd.DataFrame(records)
