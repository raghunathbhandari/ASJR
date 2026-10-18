#!/usr/bin/env python3
"""Rudra-Gann 15m notebook research: TA-Lib signals + visual inspection.
No orders. No same-candle entry. Data from existing ASJR Yahoo NQ 5m CSVs.
Example notebook:
 from RudraScanner.RudraGann.gann15_patterns import run, plot_signal
 data, signals = run("2026-10-15")
 plot_signal(data, signals, 0)
"""
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "ResearchData" / "Gann"
PATTERNS = {
    "CDLMORNINGSTAR": ("BUY", "Morning Star"),
    "CDLEVENINGSTAR": ("SELL", "Evening Star"),
    "CDLHAMMER": ("BUY", "Hammer"),
    "CDLINVERTEDHAMMER": ("BUY", "Inverted Hammer"),
    "CDLSHOOTINGSTAR": ("SELL", "Shooting Star"),
    "CDLHANGINGMAN": ("SELL", "Hanging Man"),
    "CDLENGULFING": (None, "Engulfing"),
    "CDLHARAMI": (None, "Harami"),
}
def _talib():
    try:
        import talib
    except ImportError as e:
        raise ImportError("Install TA-Lib in your notebook kernel: %pip install TA-Lib mplfinance") from e
    return talib

def load_15m(date: str, root: Path = ROOT) -> pd.DataFrame:
    """Only complete three-5m-bar groups; NY clock alignment."""
    path = Path(root) / f"NQ_{date}_5m.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}. Existing Yahoo NQ 5m daily archive required.")
    d = pd.read_csv(path)
    needed = {"datetime_ny","Open","High","Low","Close"}
    if not needed.issubset(d.columns):
        raise ValueError(f"Wrong CSV columns: {sorted(d.columns)}")
    d["time"] = pd.to_datetime(d["datetime_ny"], utc=True).dt.tz_convert("America/New_York")
    d = d.sort_values("time").drop_duplicates("time").set_index("time")
    idx = d.index
    d["bucket"] = idx.floor("15min")
    rows = []
    for _, g in d.groupby("bucket", sort=True):
        start = g["bucket"].iloc[0]
        times = pd.date_range(start, periods=3, freq="5min")
        if len(g) != 3 or not g.index.equals(times): continue
        rows.append({"time":start, "Open":float(g.Open.iloc[0]),
                     "High":float(g.High.max()),"Low":float(g.Low.min()),
                     "Close":float(g.Close.iloc[-1]), "Volume":float(g.Volume.sum()) if "Volume" in g else 0})
    if not rows: raise ValueError(f"No complete 15m bars: {path}")
    return pd.DataFrame(rows).set_index("time")

def gann_levels(lo:float, hi:float)->list[float]:
    # Odd n -> n²; even n -> n²+1. Fixed index price scale.
    return [float(n*n + (n%2 == 0)) for n in range(max(1,int(math.sqrt(max(0,lo)))-4),
             int(math.sqrt(hi))+5) if lo-100 <= n*n+(n%2==0) <= hi+100]

def detect_patterns(d:pd.DataFrame)->pd.DataFrame:
    lib=_talib()
    o,h,l,c=(d[k].to_numpy(dtype=float) for k in ("Open","High","Low","Close"))
    found=[]
    for fn,(direction,name) in PATTERNS.items():
        scores=getattr(lib,fn)(o,h,l,c)
        found.append((name,direction,scores))
    df=pd.DataFrame(index=d.index)
    for name,direction,score in found:
        df[name] = score
    return df

def scan(d:pd.DataFrame, proximity:float=15.0, context_bars:int=3,
         rr:float=2.0, sl_buffer:float=0.25, max_risk:float=150.0,
         require_close_side:bool=True)->pd.DataFrame:
    """Pattern must occur close to level (past 3 candles), match direction;
    entry NEXT complete 15m open. Conservative stop-first on OHLC ambiguity.
    Scan is research heuristic, not identical to older 5m V1 breaker state machine.
    """
    if len(d)<6: return pd.DataFrame()
    scores=detect_patterns(d)
    lvls=gann_levels(float(d.Low.min()),float(d.High.max()))
    result=[];busy=-1
    for i in range(max(3,context_bars-1),len(d)-1):
        if i<=busy:continue
        b=d.iloc[i]
        choices=[]
        for name,(base_direction,_) in []:pass
        for name in scores.columns:
            val=int(scores.iloc[i][name])
            if not val: continue
            direction = ("BUY" if val>0 else "SELL") if name in ("Engulfing","Harami") else PATTERNS_NEXT[name]
            if direction=="BUY" and val<0 or direction=="SELL" and val>0:continue
            choices.append((direction,name,val))
        if not choices: continue
        ctx=d.iloc[max(0,i-context_bars+1):i+1]
        for level in lvls:
            distance=min(float(abs(ctx.High-level).min()), float(abs(ctx.Low-level).min()))
            # Include wick overlap even if no exact high/low near line.
            if float(ctx.Low.min())<=level<=float(ctx.High.max()):distance=0
            if distance>proximity:continue
            for direction,name,score in choices:
                if require_close_side and ((direction=="BUY" and b.Close<=level) or (direction=="SELL" and b.Close>=level)):
                    continue
                # Pattern reversal check: bar closes bullish/bearish; some 3-bar patterns may do this naturally.
                if (direction=="BUY" and b.Close<=b.Open) or (direction=="SELL" and b.Close>=b.Open):continue
                nxt=d.iloc[i+1]
                entry=float(nxt.Open)
                # Two/three-candle pattern extremes including confirmation; risk known before entry.
                length=3 if name in ("Morning Star","Evening Star") else 2 if name in ("Engulfing","Harami") else 1
                pattern_bars=d.iloc[max(0,i-length+1):i+1]
                stop=round((float(pattern_bars.Low.min())-sl_buffer)*4)/4 if direction=="BUY" else round((float(pattern_bars.High.max())+sl_buffer)*4)/4
                risk=(entry-stop) if direction=="BUY" else (stop-entry)
                if not (0.25<=risk<=max_risk):continue
                target=round((entry+rr*risk if direction=="BUY" else entry-rr*risk)*4)/4
                outcome="END";exit_ix=len(d)-1;exit_price=float(d.Close.iloc[-1])
                for j in range(i+1,len(d)):
                    x=d.iloc[j]
                    hit_stop = x.Low<=stop if direction=="BUY" else x.High>=stop
                    hit_tp = x.High>=target if direction=="BUY" else x.Low<=target
                    if hit_stop:
                        outcome="SL";exit_ix=j;exit_price=stop;break
                    if hit_tp:
                        outcome="TP";exit_ix=j;exit_price=target;break
                signed=(exit_price-entry) if direction=="BUY" else (entry-exit_price)
                result.append({
                    "signal_time_ny":str(d.index[i]),"signal_time_uk":str(d.index[i].tz_convert("Europe/London")),
                    "direction":direction,"candle_pattern":name,"pattern_score":score,
                    "reason":f"{name}; Gann {level:.0f} within {distance:.2f} pts over last {context_bars} bars; confirmed close {'above' if direction=='BUY' else 'below'} line",
                    "gann":level,"signal_close":float(b.Close),"entry_time_ny":str(d.index[i+1]),"entry":entry,
                    "SL":stop,"TP":target,"result":outcome,"exit_time_ny":str(d.index[exit_ix]),
                    "exit_price":exit_price,"gain_loss_pct":round(signed/entry*100,4),
                    "R":round(signed/risk,3),"signal_ix":i,"exit_ix":exit_ix,
                })
                busy=exit_ix
                break
            if i<=busy:break
    return pd.DataFrame(result)

PATTERNS_NEXT={"Morning Star":"BUY","Evening Star":"SELL","Hammer":"BUY","Inverted Hammer":"BUY",
               "Shooting Star":"SELL","Hanging Man":"SELL"}

def run(date:str="2026-10-15", root:Path=ROOT, **kwargs):
    d=load_15m(date,root)
    signals=scan(d,**kwargs)
    print(f"RUDRA GANN | {date} | 15m | {len(d)} complete candles | {len(signals)} signals")
    if not signals.empty:
        for _,s in signals.iterrows():
            print(f"{s.signal_time_ny} | {s.direction} | {s.candle_pattern} | G{s.gann:.0f}")
            print(f"  Signal reason: {s.reason}")
            print(f"  Entry {s.entry:.2f} | SL {s.SL:.2f} | TP {s.TP:.2f} | {s.result} | gain/loss {s.gain_loss_pct:+.3f}% | {s.R:+.2f}R")
        print(f"TOTAL | {signals.R.sum():+.2f}R gross | index-point % not account return; fees/slippage excluded")
    return d,signals

def plot_signal(d:pd.DataFrame,signals:pd.DataFrame,number:int=0,candles:int=10):
    """Display EXACTLY 8-10 candles as candlesticks with Gann horizontal line."""
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    if signals.empty:raise ValueError("No detected signals to plot")
    if not 8<=candles<=10:raise ValueError("candles must be 8, 9 or 10")
    s=signals.iloc[number]
    ix=int(s.signal_ix)
    left=max(0,ix-5);right=min(len(d),left+candles);left=max(0,right-candles)
    panel=d.iloc[left:right]
    plots=[mpf.make_addplot(np.full(len(panel),float(s.gann)),color="goldenrod",width=1.4)]
    fig,ax=mpf.plot(panel,type="candle",style="yahoo",addplot=plots,
                    figsize=(12,5),returnfig=True,volume=False,show_nontrading=False,
                    title=f"{s.direction} | {s.candle_pattern} | Gann {s.gann:.0f} | signal {s.signal_time_ny}")
    if ix>=left and ix<right:
        ax[0].axvline(ix-left,color="royalblue",linestyle="--",alpha=.8)
    plt.show()
    return fig


def print_full_day(d:pd.DataFrame, signals:pd.DataFrame):
    """Print ALL complete 15-minute candles and mark signal, entry and exit bars."""
    marked={}
    for k,s in signals.iterrows():
        marked.setdefault(int(s.signal_ix),[]).append(f"SIGNAL {k+1} {s.direction} {s.candle_pattern}")
        marked.setdefault(int(s.signal_ix)+1,[]).append(f"ENTRY {k+1} PURPLE")
        marked.setdefault(int(s.exit_ix),[]).append(f"EXIT {k+1} {s.result}")
    full=d[["Open","High","Low","Close"]].copy()
    full.insert(0,"NY_time",[t.strftime("%H:%M") for t in d.index])
    full["Marker"]=["; ".join(marked.get(i,[])) for i in range(len(full))]
    print(full.to_string(index=False))
    if signals.empty:
        print("NO SIGNALS: no entries or exits to mark.")
    else:
        summary=signals[["signal_time_ny","direction","candle_pattern","reason",
                        "entry_time_ny","entry","SL","TP","result","exit_time_ny",
                        "exit_price","gain_loss_pct","R"]].copy()
        print("\\nSIGNAL AND TRADE SUMMARY")
        print(summary.to_string(index=False))
    return full


def plot_full_day(d:pd.DataFrame, signals:pd.DataFrame, title:str="Rudra-Gann 15m Full Day"):
    """Plot EVERY complete 15m candle, horizontal Gann lines and all entry/exit markers.

    Purple triangle = actual next-bar opening entry assumption.
    Green X = take-profit, Red X = stop-loss, gray X = end-of-data mark.
    The display is research only; full-session bars need not be continuous around
    exchange market breaks, and intrabar OHLC cannot establish order of TP/SL.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import mplfinance as mpf

    if d.empty:raise ValueError("No bars to plot")
    fig, axes = mpf.plot(d,type="candle",style="yahoo",volume=False,
                         show_nontrading=False,returnfig=True,
                         figsize=(19,8), title=title,
                         xrotation=45,datetime_format="%H:%M",
                         tight_layout=True)
    ax=axes[0]
    levels=sorted({float(x) for x in signals["gann"]}) if not signals.empty else gann_levels(float(d.Low.min()),float(d.High.max()))
    low=float(d.Low.min());high=float(d.High.max())
    for level in levels:
        if low-60 <= level <= high+60:
            ax.axhline(level,color="goldenrod",linestyle="--",linewidth=1.1,alpha=.85)
            ax.text(len(d)-0.5,level,f" G {level:.0f}",color="darkgoldenrod",
                    ha="right",va="bottom",fontsize=9)

    for k,s in signals.iterrows():
        ent=int(s.signal_ix)+1
        out=int(s.exit_ix)
        if 0<=ent<len(d):
            ax.scatter([ent],[float(s.entry)],marker="^" if s.direction=="BUY" else "v",
                       s=140,facecolor="purple",edgecolor="white",linewidth=1.0,zorder=8)
            ax.annotate(f" E{k+1}",(ent,float(s.entry)),xytext=(5,12 if s.direction=="BUY" else -18),
                        textcoords="offset points",color="purple",fontsize=9,fontweight="bold")
        if 0<=out<len(d):
            color="green" if s.result=="TP" else "red" if s.result=="SL" else "gray"
            ax.scatter([out],[float(s.exit_price)],marker="x",s=145,c=color,
                       linewidth=2.7,zorder=9)
            ax.annotate(f" X{k+1} {s.result}",(out,float(s.exit_price)),xytext=(6,-15),
                        textcoords="offset points",color=color,fontsize=9,fontweight="bold")

    ax.legend(handles=[
        Line2D([0],[0],color="goldenrod",linestyle="--",label="Gann lines"),
        Line2D([0],[0],marker="^",linestyle="None",markerfacecolor="purple",
               markeredgecolor="white",markersize=11,label="Entry (purple)"),
        Line2D([0],[0],marker="x",linestyle="None",color="green",markersize=11,label="TP exit"),
        Line2D([0],[0],marker="x",linestyle="None",color="red",markersize=11,label="SL exit"),
        Line2D([0],[0],marker="x",linestyle="None",color="gray",markersize=11,label="END exit"),
    ],loc="best",fontsize=9)
    plt.show()
    return fig


def full_day(date:str="2026-10-16",root:Path=ROOT,**kwargs):
    """One notebook call: complete 15m CSV, pattern report and whole-day chart."""
    d,signals=run(date,root=root,**kwargs)
    print_full_day(d,signals)
    plot_full_day(d,signals,title=f"NQ | {date} | 15-minute | Full Day | Gann/TA-Lib")
    return d,signals

if __name__=="__main__":
    run()
