"""Experimental early EMA9 crossing, following September chart review.

No date-specific rules. Replaces break10 and delayed five-bar trend gates.
This is a candidate entry rule, not a validated flat-area classifier.
Uses completed bars, provisional source VWAP, hypothetical close fills.
"""
import pandas as pd
import numpy as np


def normalized_angles(data, angle_bars=3):
    """Signed angle: horizontal unit = angle_bars bars; vertical unit = 1 ATR.

    Uses endpoint displacement over 15 minutes by default, not screen geometry.
    Positive angles mean rising. Windows must be contiguous within RTH.
    """
    if not isinstance(angle_bars, int) or angle_bars < 1:
        raise ValueError('angle_bars must be a positive integer')
    valid = data.Session.eq(data.Session.shift(angle_bars))
    valid &= (data.Datetime-data.Datetime.shift(angle_bars)).eq(pd.Timedelta(minutes=5*angle_bars))
    valid &= data.RTH.rolling(angle_bars+1).sum().eq(angle_bars+1)
    atr=data.ATR.where(data.ATR>0)
    return pd.DataFrame({
        'PriceAngle': np.degrees(np.arctan((data.Close-data.Close.shift(angle_bars))/atr)).where(valid),
        'EMA9Angle': np.degrees(np.arctan((data.EMA9-data.EMA9.shift(angle_bars))/atr)).where(valid)
    }, index=data.index)


def generate_cross_signals(data, max_gap_atr=0.75, min_time_rvol=0.5,
                           angle_min=None, angle_max=70, angle_bars=3):
    previous = data.shift(1)
    contiguous = (data.Datetime - previous.Datetime).eq(pd.Timedelta(minutes=5))
    mask = (
        data.RTH & previous.RTH.eq(True)
        & data.Session.eq(previous.Session) & contiguous
        & (previous.Close <= previous.EMA9) & (data.Close > data.EMA9)
        & (data.Close > data.VWAP) & (data.EMA9 > previous.EMA9)
        & (data.Close > data.Open) & (data.Volume > 0)
        & data.EMAGapATR.between(0, max_gap_atr)
        & (data.TimeRVOLMean >= min_time_rvol)
    )
    if angle_min is not None:
        if not 0 <= angle_min < angle_max <= 90:
            raise ValueError('Require 0 <= angle_min < angle_max <= 90')
        angles=normalized_angles(data,angle_bars)
        mask &= angles.PriceAngle.ge(angle_min) & angles.PriceAngle.lt(angle_max)
        mask &= angles.EMA9Angle.ge(angle_min) & angles.EMA9Angle.lt(angle_max)
    return mask.fillna(False).to_numpy(dtype=bool)


def generate_confirmed_signals(data, config):
    """A recent crossing may confirm later, while remaining above EMA9.

    A return to/below EMA9 or a session/data gap invalidates the old crossing.
    No date exceptions or future candles. Distance remains an independent gate.
    """
    prev=data.shift(1)
    contiguous=data.Session.eq(prev.Session) & (data.Datetime-prev.Datetime).eq(pd.Timedelta(minutes=5))
    cross=data.RTH & prev.RTH.eq(True) & contiguous & (prev.Close<=prev.EMA9) & (data.Close>data.EMA9)
    recent=cross.copy()
    for age in range(1,config.get('confirmation_bars',3)+1):
        valid=cross.shift(age,fill_value=False)
        for k in range(age):
            valid &= (data.Close>data.EMA9).shift(k,fill_value=False)
            valid &= contiguous.shift(k,fill_value=False) & data.RTH.shift(k,fill_value=False)
        recent |= valid
    angles=normalized_angles(data,config.get('angle_bars',3))
    pmin,pmax=config.get('price_angle_range',[20,70])
    emin,emax=config.get('ema_angle_range',[3,55])
    mask=(recent & data.RTH & (data.Close>data.VWAP)
          & (data.Close>prev.Close) & (data.EMA9>prev.EMA9) & (data.Close>data.Open)
          & angles.PriceAngle.between(pmin,pmax) & angles.EMA9Angle.between(emin,emax)
          & data.EMAGapATR.between(0,config.get('max_gap_atr',.75))
          & (data.Volume>0) & (data.TimeRVOLMean>=config.get('min_time_rvol',.5)))
    return mask.fillna(False).to_numpy(dtype=bool)
