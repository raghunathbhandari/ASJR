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

# ================================================================
# EDIT SIGNAL RULES HERE: each filter returns True (PASS) / False.
# TA-Lib detection is separate from Gann, structure and risk filters.
# ================================================================

def pattern_is_direction(name: str, score: int, side: str) -> bool:
    """True when TA-Lib named candle pattern supports BUY or SELL."""
    if score == 0:
        return False
    detected = ("BUY" if score > 0 else "SELL") if name in ("Engulfing", "Harami") else PATTERNS_NEXT[name]
    return detected == side and ((score > 0) == (side == "BUY"))


def find_candle_patterns(scores: pd.DataFrame, candle_index: int, side: str):
    """All confirmed third-party TA-Lib patterns at this candle for a side."""
    matches = []
    for name in scores.columns:
        score = int(scores.iloc[candle_index][name])
        if pattern_is_direction(name, score, side):
            matches.append((name, score))
    return matches


def filter_gann_touch(context: pd.DataFrame, level: float, proximity: float) -> bool:
    """Gann touched or within proximity in the context-window candles."""
    low, high = float(context.Low.min()), float(context.High.max())
    if low <= level <= high:
        return True
    distance = min(float(abs(context.High - level).min()),
                   float(abs(context.Low - level).min()))
    return distance <= proximity


def gann_distance(context: pd.DataFrame, level: float) -> float:
    """Distance in NQ points (zero when any candle crosses the line)."""
    if float(context.Low.min()) <= level <= float(context.High.max()):
        return 0.0
    return min(float(abs(context.High - level).min()),
               float(abs(context.Low - level).min()))


def filter_close_on_gann_side(candle, level: float, side: str) -> bool:
    """SELL closes below resistance; BUY closes above support."""
    return bool(candle.Close < level if side == "SELL" else candle.Close > level)


def filter_reversal_candle(candle, side: str) -> bool:
    """SELL red candle; BUY green candle. Touch alone is never an entry."""
    return bool(candle.Close < candle.Open if side == "SELL"
                else candle.Close > candle.Open)


def filter_structure_break(candle, previous_candle, side: str) -> bool:
    """SELL close breaks previous 15m low; BUY breaks previous 15m high."""
    return bool(candle.Close < previous_candle.Low if side == "SELL"
                else candle.Close > previous_candle.High)


def filter_strong_body(candle, min_body_ratio: float = 0.40) -> bool:
    """True when real body is >=40% of the full candle range."""
    span = float(candle.High - candle.Low)
    return span > 0 and abs(float(candle.Close - candle.Open)) / span >= min_body_ratio


def filter_retest_after_pattern(d: pd.DataFrame, anchor: int, signal_index: int,
                                level: float, side: str, proximity: float) -> bool:
    """TA-Lib pattern -> subsequent higher-high/lower-low retest near Gann."""
    segment = d.iloc[anchor + 1:signal_index]
    if segment.empty:
        return False
    if side == "SELL":
        extremum = float(segment.High.max())
        return extremum > float(d.iloc[anchor].High) and abs(extremum-level) <= proximity+25
    extremum = float(segment.Low.min())
    return extremum < float(d.iloc[anchor].Low) and abs(extremum-level) <= proximity+25


def filter_risk(risk: float, max_risk: float = 150.0) -> bool:
    """Allow 1 NQ tick minimum and limited index-point stop distance."""
    return 0.25 <= risk <= max_risk


def scan(d:pd.DataFrame, proximity:float=15.0, context_bars:int=3,
         rr:float=2.0, sl_buffer:float=0.25, max_risk:float=150.0,
         require_close_side:bool=True)->pd.DataFrame:
    """Pattern must occur close to level (past 3 candles), match direction;
    signal candle closes on right side of V; simulated entry at that close, exits begin on next candle.
    Scan is research heuristic, not identical to older 5m V1 breaker state machine.
    """
    if len(d)<6: return pd.DataFrame()
    scores=detect_patterns(d)
    lvls=gann_levels(float(d.Low.min()),float(d.High.max()))
    result=[];busy=-1
    for i in range(max(3,context_bars-1),len(d)-1):
        if i<=busy:continue
        b=d.iloc[i]
        choices=[(side,name,score) for side in ("BUY","SELL")
                 for name,score in find_candle_patterns(scores,i,side)]
        if not choices: continue
        ctx=d.iloc[max(0,i-context_bars+1):i+1]
        for level in lvls:
            if not filter_gann_touch(ctx,level,proximity):continue
            distance=gann_distance(ctx,level)
            for direction,name,score in choices:
                if require_close_side and not filter_close_on_gann_side(b,level,direction):continue
                if not filter_reversal_candle(b,direction):continue
                if not filter_structure_break(b,d.iloc[i-1],direction):continue
                # The TA-Lib pattern candle itself is the directional right-side signal.
                # Close-price entry is an idealized fill after full candle confirmation.
                entry=float(b.Close)
                # Two/three-candle pattern extremes including confirmation; risk known before entry.
                length=3 if name in ("Morning Star","Evening Star") else 2 if name in ("Engulfing","Harami") else 1
                pattern_bars=d.iloc[max(0,i-length+1):i+1]
                stop=round((float(pattern_bars.Low.min())-sl_buffer)*4)/4 if direction=="BUY" else round((float(pattern_bars.High.max())+sl_buffer)*4)/4
                risk=(entry-stop) if direction=="BUY" else (stop-entry)
                if risk<=0:continue
                risk_ok=filter_risk(risk,max_risk)
                target=round((entry+rr*risk if direction=="BUY" else entry-rr*risk)*4)/4
                outcome="END" if risk_ok else "SKIP_RISK"
                exit_ix=len(d)-1 if risk_ok else i
                exit_price=float(d.Close.iloc[-1]) if risk_ok else entry
                for j in (range(i+1,len(d)) if risk_ok else []):
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
                    "reason":f"{name}; Gann {level:.0f} within {distance:.2f} pts over last {context_bars} bars; confirmed close {'above' if direction=='BUY' else 'below'} line; prior-bar {'high broken' if direction=='BUY' else 'low broken'}; {'bullish rising V' if direction=='BUY' else 'bearish falling inverted-V'} signal candle CLOSE (assumed fill)",
                    "gann":level,"signal_close":float(b.Close),"entry_time_ny":str(d.index[i]),"entry_ix":i,"entry":entry,
                    "SL":stop,"TP":target,"result":outcome,"exit_time_ny":str(d.index[exit_ix]),
                    "exit_price":exit_price,"gain_loss_pct":round(signed/entry*100,4),
                    "R":round(signed/risk,3),"signal_ix":i,"exit_ix":exit_ix,"risk_ok":risk_ok,
                })
                busy=exit_ix
                break
            if i<=busy:break
    # Delayed confirmation: a TA-Lib reversal pattern can appear BEFORE the
    # Gann retest has finished. Do not enter on that first bearish candle.
    # Keep its evidence, wait for a HIGHER HIGH near resistance, and confirm
    # a breakdown under the previous 15m low with a strong bearish candle.
    # BUY is the symmetric lower-low and break-above-previous-high case.
    # This branch is independent of the direct confirmation above.
    for i in range(4,len(d)-1):
        if any(t["signal_ix"]<=i<=t["exit_ix"] for t in result):
            continue
        b=d.iloc[i]
        prev=d.iloc[i-1]
        for direction in ("SELL","BUY"):
            if not filter_reversal_candle(b,direction):continue
            if not filter_structure_break(b,prev,direction):continue
            if not filter_strong_body(b):continue
            found=None
            for anchor in range(max(1,i-5),i-1):
                names=[name for name,_ in find_candle_patterns(scores,anchor,direction)]
                if not names:continue
                for level in lvls:
                    if not filter_retest_after_pattern(d,anchor,i,level,direction,proximity):continue
                    if require_close_side and not filter_close_on_gann_side(b,level,direction):continue
                    entry=float(b.Close)
                    if direction=="SELL":
                        stop=math.ceil((float(b.High)+sl_buffer)*4)/4
                        risk=stop-entry
                    else:
                        stop=math.floor((float(b.Low)-sl_buffer)*4)/4
                        risk=entry-stop
                    if filter_risk(risk,max_risk):
                        found=(anchor,names[0],level,entry,stop,risk)
                        break
                if found:break
            if not found:continue
            anchor,name,level,entry,stop,risk=found
            target=round((entry+rr*risk if direction=="BUY" else entry-rr*risk)*4)/4
            outcome="END";exit_ix=len(d)-1;exit_price=float(d.Close.iloc[-1])
            for j in range(i+1,len(d)):
                x=d.iloc[j]
                if (x.Low<=stop if direction=="BUY" else x.High>=stop):
                    outcome="SL";exit_ix=j;exit_price=stop;break
                if (x.High>=target if direction=="BUY" else x.Low<=target):
                    outcome="TP";exit_ix=j;exit_price=target;break
            # This is a signal-review chart: preserve valid signals even if paper holding periods overlap.
            if any(t["signal_ix"] == i and t["direction"] == direction for t in result):
                continue
            signed=(exit_price-entry) if direction=="BUY" else (entry-exit_price)
            result.append({
                "signal_time_ny":str(d.index[i]),
                "signal_time_uk":str(d.index[i].tz_convert("Europe/London")),
                "direction":direction,
                "candle_pattern":f"{name} + retest/structure confirmation",
                "pattern_score":int(scores.iloc[anchor][name]),
                "reason":f"TA-Lib {name} at {d.index[anchor].strftime('%H:%M')} NY; Gann {level:.0f} retest made a new {'lower low' if direction=='BUY' else 'higher high'}; confirmation breaks previous 15m {'high' if direction=='BUY' else 'low'} at {d.index[i].strftime('%H:%M')} NY",
                "gann":level,"signal_close":float(b.Close),
                "entry_time_ny":str(d.index[i]),"entry_ix":i,"entry":entry,
                "SL":stop,"TP":target,"result":outcome,
                "exit_time_ny":str(d.index[exit_ix]),"exit_price":exit_price,
                "gain_loss_pct":round(signed/entry*100,4),
                "R":round(signed/risk,3),"signal_ix":i,"exit_ix":exit_ix,
            })
            break
    result.sort(key=lambda x:x["signal_ix"])
    # Strict mode: TA-Lib named reversal pattern is mandatory.
    # A Gann touch, a green retest candle, or structural V shape alone
    # must never create a BUY or SELL trade.
    return pd.DataFrame(result)

PATTERNS_NEXT={"Morning Star":"BUY","Evening Star":"SELL","Hammer":"BUY","Inverted Hammer":"BUY",
               "Shooting Star":"SELL","Hanging Man":"SELL"}

def run(date:str="2026-10-15", root:Path=ROOT, **kwargs):
    """Collect signals; full_day() owns display order and output."""
    d=load_15m(date,root)
    signals=scan(d,**kwargs)
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
    """Summary -> three signal reasons -> concise signal table -> chart heading."""
    count=len(signals)
    winners=int((signals["result"]=="TP").sum()) if count else 0
    losers=int((signals["result"]=="SL").sum()) if count else 0
    rejected=int((signals["result"]=="SKIP_RISK").sum()) if count else 0
    pending=count-winners-losers-rejected
    decided=winners+losers
    rate=(100*winners/decided) if decided else 0.
    print("SUMMARY")
    print(f"{count} signals | {rate:.1f}% win rate (resolved trades) | {winners} good | {losers} fail | {pending} END/unresolved | {rejected} risk-rejected")
    print("Orange circles = valid pattern/structure signal rejected by risk limit (not an entry).")
    print("Note: overlapping signals are independent tests, not one-position portfolio returns.")
    print("\\n---\\n")
    for num,(_,s) in enumerate(signals.iterrows(),1):
        print(f"SIGNAL {num} | {s.direction} | {s.candle_pattern} | {s.signal_time_ny}")
        print(f"  Reason 1: Gann {s.gann:.0f} retest/proximity and reversal setup")
        print(f"  Reason 2: {s.reason}")
        print(f"  Reason 3: Confirmed 15m signal close {s.signal_close:.2f}; assumed entry at close")
        print(f"  Outcome: {s.result} | {s.gain_loss_pct:+.3f}% | {s.R:+.2f}R")
        print()
    print("---\\nSIGNALS TABLE")
    rows=[]
    for num,(_,s) in enumerate(signals.iterrows(),1):
        b=d.iloc[int(s.signal_ix)]
        rows.append({"#":num,"NY time":s.signal_time_ny,
                     "Side":s.direction,"Pattern":s.candle_pattern,
                     "Gann":s.gann,"O":b.Open,"H":b.High,"L":b.Low,"C":b.Close,
                     "Entry":s.entry,"SL":s.SL,"TP":s.TP,
                     "Result":s.result,"Gain/Loss %":s.gain_loss_pct,"R":s.R})
    result=pd.DataFrame(rows)
    if count:print(result.to_string(index=False))
    else:print("No confirmed reversal signals.")
    print("\\n---\\nCHART")
    return result

def plot_full_day(d:pd.DataFrame, signals:pd.DataFrame, title:str="Rudra-Gann 15m Full Day"):
    """Plot EVERY complete 15m candle, horizontal Gann lines and all entry/exit markers.

    Purple triangle = TA-Lib signal 15m candle CLOSE (idealized fill).
    Green X = take-profit, Red X = stop-loss, gray X = end-of-data mark.
    The display is research only; full-session bars need not be continuous around
    exchange market breaks, and intrabar OHLC cannot establish order of TP/SL.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import mplfinance as mpf

    if d.empty:raise ValueError("No bars to plot")
    dark_style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        facecolor="#111111",
        figcolor="#111111",
        edgecolor="#666666",
        gridcolor="#333333",
        gridstyle="-",
        rc={"axes.labelcolor":"white", "xtick.color":"white",
            "ytick.color":"white", "text.color":"white",
            "axes.titlecolor":"white"},
    )
    fig, axes = mpf.plot(d,type="candle",style=dark_style,volume=False,
                         show_nontrading=False,returnfig=True,
                         figsize=(13,5), title=title,
                         xrotation=45,datetime_format="%H:%M",
                         tight_layout=True)
    ax=axes[0]
    levels=gann_levels(float(d.Low.min()),float(d.High.max()))
    low=float(d.Low.min());high=float(d.High.max())
    for level in levels:
        if low-60 <= level <= high+60:
            ax.axhline(level,color="gold",linestyle="--",linewidth=1.1,alpha=.85)
            ax.text(len(d)-0.5,level,f" G {level:.0f}",color="gold",
                    ha="right",va="bottom",fontsize=9)

    for k,s in signals.iterrows():
        ent=int(s.entry_ix)
        out=int(s.exit_ix)
        if 0<=ent<len(d):
            is_skipped=s.result=="SKIP_RISK"
            ax.scatter([ent],[float(s.entry)],marker="o" if is_skipped else ("^" if s.direction=="BUY" else "v"),
                       s=140,facecolor="orange" if is_skipped else "purple",edgecolor="white",linewidth=1.0,zorder=8)
            ax.annotate(f" E{k+1}",(ent,float(s.entry)),xytext=(5,12 if s.direction=="BUY" else -18),
                        textcoords="offset points",color="purple",fontsize=9,fontweight="bold")
        if 0<=out<len(d) and s.result!="SKIP_RISK":
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
        Line2D([0],[0],marker="o",linestyle="None",markerfacecolor="orange",
               markeredgecolor="white",markersize=10,label="Signal rejected by risk"),
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
