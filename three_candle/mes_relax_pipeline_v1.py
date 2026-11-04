#!/usr/bin/env python3
"""MES Relax v1: editable, structure-aware nine-method research pipeline.

Stages: candle_detect_core -> market_structure -> swing_sr_lines ->
volume_detect -> wicks_detect -> daily_range_check ->
display_other_metrics -> higher_timeframe_support -> Liquidity_area_detect.

Only CORE-TRUE candidates are plotted in "all"; "good" means passing every
currently REQUIRED check. The original scanner and historical data are NOT
modified. No orders are placed. UK times on all labels.

Examples (run from repo root after pulling latest main):
    python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-29 --plot-both
    python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-30 --plot-both
    python3 three_candle/mes_relax_pipeline_v1.py --date 2026-10-30 --plot-both --show-wait
Requires matplotlib only for plotting. CSV scanning uses standard library.

User-owned tuning switches and thresholds below; each stage has a clear
function so future edits don't mix candle detection with market analysis.
"""
import argparse
import csv
from datetime import timedelta
from pathlib import Path

import mes_relax_structure_first_v1 as base

# ===== EASY-TO-EDIT SETTINGS ===============================================
LOOK_AHEAD_C3_BARS = 3             # Max C3 delay; C3 must CLOSE directionally
MIN_SWEEP_POINTS = 2.0             # Filter 1: sufficient liquidity sweep
MIN_C2_REJECTION_WICK_X = 2.0      # Filter 2: directional C2 wick/body ratio
MAX_LONG_WICKS_IN_5 = 1           # Filter 3: 2 of 5 => WAIT
LONG_WICK_MODE = "both"           # 'both' upper+lower; 'either' one side
MIN_C3_CLOSE_CONFIRMATION = True  # Filter 4: C3 must close beyond C2 body
REQUIRE_MARKET_ALIGNMENT = True   # Structure is directional, not candle colour
REQUIRE_SWING_SR_TOUCH = False    # Level touch recorded; optional hard filter
# All further sections are INFORMATIONAL until the user selects thresholds.
REQUIRE_VOLUME = False
REQUIRE_DAILY_RANGE = False
REQUIRE_HTF = False
REQUIRE_LIQUIDITY_AREA = False

# The original 5-point SL / 10-point TP chart reference is visual only:
REFERENCE_STOP_POINTS = 5.0
REFERENCE_TARGET_POINTS = 10.0
CANDLE_LOOKBACK = 6
CANDLE_LOOKFORWARD = 7
PLOT_COLUMNS = 2
# ============================================================================
ROOT = Path(__file__).resolve().parent


def candle_detect_core(bars, c1_i, c2_i, c3_i, side):
    """STAGE 1: direction-neutral C1/C2/C3 detection; no later market filters.

    Both sides are checked separately, regardless of which other side is
    pending. C2 must sweep C1; C3 must confirm by DIRECTIONAL BODY CLOSE,
    not just a wick touching the opposite boundary. No future data is used.
    The sweep can be small here: quality checks decide whether to trade.
    """
    c1, c2, c3 = bars[c1_i], bars[c2_i], bars[c3_i]
    sweep = c1.l-c2.l if side=="BUY" else c2.h-c1.h
    if sweep <= 0:
        return None
    # Structural invalidation: C3 breaches the swept C2 extreme.
    if side=="BUY" and c3.l<c2.l or side=="SELL" and c3.h>c2.h:
        return None
    boundary = max(c2.o,c2.c) if side=="BUY" else min(c2.o,c2.c)
    confirmed = (c3.c>boundary and c3.c>c3.o if side=="BUY"
                 else c3.c<boundary and c3.c<c3.o)
    if not confirmed:
        return None
    return {"side":side,"sweep_points":round(sweep,3),
            "c3_boundary":boundary,"core_confirmed":True}


def market_structure(bars, c3_i):
    """STAGE 2: use CONFIRMED HH/HL or LH/LL pivots, never future pivots.

    Pivots need two subsequent fully closed 15m candles. Mixed means RANGE.
    Upward-trending context supports BUY, downward supports SELL.
    """
    highs,lows=base.confirmed_pivots(bars,c3_i)
    return {"market_structure":base.classify_structure(highs,lows),
            "swing_highs":highs,"swing_lows":lows}


def swing_sr_lines(bars, c2_i, c3_i, side, structure):
    """STAGE 3: price-level / swing S-R lines; returns confirmed levels.

    Structure lines are horizontal from confirmed swing pivots. Level touch
    is informational by default: enable REQUIRE_SWING_SR_TOUCH to gate.
    """
    levels=structure["swing_lows"] if side=="BUY" else structure["swing_highs"]
    reference=levels[-1][1] if levels else None
    c2=bars[c2_i]
    touch=(reference is not None and
           (c2.l<=reference+base.LEVEL_TOLERANCE_POINTS if side=="BUY"
            else c2.h>=reference-base.LEVEL_TOLERANCE_POINTS))
    return {"sr_reference":reference,"sr_touch":touch,
            "sr_lines":[round(v,2) for _,v in levels[-5:]]}


def volume_detect(bars, c2_i, c3_i):
    """STAGE 4: RVOL from preceding 20 15m candles; no fabricated volume.

    This stage is informational. Set REQUIRE_VOLUME=True and implement a
    threshold below only AFTER testing the effect on both winners and losers.
    """
    preceding=bars[max(0,c2_i-20):c2_i]
    mean=sum(x.v for x in preceding)/len(preceding) if len(preceding)==20 else None
    rvol=bars[c2_i].v/mean if mean and mean>0 else None
    # Current placeholder gate: only require valid RVOL if enabled.
    return {"c2_rvol20":round(rvol,3) if rvol is not None else None,
            "volume_ok":rvol is not None}


def wicks_detect(bars,c2_i,c3_i,side):
    """STAGE 5: rejection wick strength + 5-candle chop/WAIT rule.

    A single long C2 directional wick is DESIRED. Two or more candles in the
    last five with BOTH upper AND lower wick >= max(body,.25) => WAIT.
    Change LONG_WICK_MODE='either' for a stricter alternative.
    """
    c2=bars[c2_i]; body,up,down=base.wick_sizes(c2)
    ratio=(down if side=="BUY" else up)/max(body,.25)
    window=bars[c3_i-4:c3_i+1] if c3_i>=4 else []
    count=0
    for c in window:
        body1,up1,down1=base.wick_sizes(c)
        threshold=max(body1,.25)
        flag=(up1>=threshold and down1>=threshold if LONG_WICK_MODE=="both"
              else up1>=threshold or down1>=threshold)
        count+=int(flag)
    return {"c2_wick_body":round(ratio,3),"last5_long_wicks":count,
            "wick_strong":ratio>=MIN_C2_REJECTION_WICK_X,
            "wick_congestion_ok":len(window)==5 and count<=MAX_LONG_WICKS_IN_5}


def daily_range_check(bars,c3_i,side):
    """STAGE 6: room-to-go estimate from completed UK-day 15m highs/lows.

    Do NOT interpret the already-observed daily range as a predictive target.
    We print distance to current-day extreme / percentage of completed range.
    """
    c3=bars[c3_i]; uk_date=c3.ts.astimezone(base.UK).date()
    past=[b for b in bars[:c3_i+1] if b.ts.astimezone(base.UK).date()==uk_date]
    hi=max(x.h for x in past);lo=min(x.l for x in past)
    room=max(0,hi-c3.c) if side=="BUY" else max(0,c3.c-lo)
    span=hi-lo
    return {"day_high":hi,"day_low":lo,"day_range_so_far":round(span,2),
            "room_to_day_extreme_points":round(room,2),
            "daily_range_ok":True} # user will decide room/ATR threshold


def display_other_metrics(bars,c1_i,c2_i,c3_i):
    """STAGE 7: data for chart labels and manual pattern inspection."""
    c2,c3=bars[c2_i],bars[c3_i]
    return {"c1_uk":bars[c1_i].ts.astimezone(base.UK).isoformat(timespec="minutes"),
            "c2_uk":c2.ts.astimezone(base.UK).isoformat(timespec="minutes"),
            "c3_uk":c3.ts.astimezone(base.UK).isoformat(timespec="minutes"),
            "c3_close":c3.c,"c2_range_points":round(c2.h-c2.l,2),
            "c3_range_points":round(c3.h-c3.l,2),
            "c3_wait_bars":c3_i-c2_i}


def higher_timeframe_support(bars,c3_i,side):
    """STAGE 8: confirmed previous H1 candle direction (context only).

    Only fully CLOSED 60-minute bars are eligible; never read the future
    part of an unfinished H1 candle. H1 alignment is NOT mandatory yet.
    """
    c3_close=bars[c3_i].ts+timedelta(minutes=15)
    h1_start=c3_close.replace(minute=0,second=0,microsecond=0)
    history=[x for x in bars[:c3_i+1] if h1_start-timedelta(hours=1)<=x.ts<h1_start]
    latest=history[-4:] if len(history)>=4 else []
    valid=(len(latest)==4 and all(
        x.ts==h1_start-timedelta(hours=1)+timedelta(minutes=15*i)
        for i,x in enumerate(latest)))
    if not valid:
        return {"h1_trend":"UNKNOWN","htf_ok":False}
    delta=latest[-1].c-latest[0].o
    trend="BULLISH" if delta>0 else "BEARISH" if delta<0 else "FLAT"
    return {"h1_trend":trend,
            "htf_ok":trend==("BULLISH" if side=="BUY" else "BEARISH")}


def Liquidity_area_detect(bars,c2_i,side,sr):
    """STAGE 9: nearby liquidity sweep against confirmed swing S/R lines.

    Separately stores whether the C2 liquidity touch has been detected.
    Do not infer institutional orders from OHLC bars alone.
    """
    level=sr["sr_reference"]
    touched=sr["sr_touch"]
    return {"liquidity_area":("SWING_LOW" if side=="BUY" else "SWING_HIGH")
                             if touched else "NONE",
            "liquidity_area_ok":bool(touched),"liquidity_level":level}


def evaluate_pipeline(bars,c1_i,c2_i,c3_i,core):
    """Apply the nine stages; every failure remains inspectable in CSV."""
    side=core["side"]
    structure=market_structure(bars,c3_i)
    sr=swing_sr_lines(bars,c2_i,c3_i,side,structure)
    volume=volume_detect(bars,c2_i,c3_i)
    wicks=wicks_detect(bars,c2_i,c3_i,side)
    day=daily_range_check(bars,c3_i,side)
    metrics=display_other_metrics(bars,c1_i,c2_i,c3_i)
    htf=higher_timeframe_support(bars,c3_i,side)
    liquidity=Liquidity_area_detect(bars,c2_i,side,sr)
    aligned=structure["market_structure"]==("BULLISH" if side=="BUY" else "BEARISH")
    checks={
        "sweep2":core["sweep_points"]>=MIN_SWEEP_POINTS,
        "wick2":wicks["wick_strong"],
        "c3_close":core["core_confirmed"] if MIN_C3_CLOSE_CONFIRMATION else True,
        "wick_congestion":wicks["wick_congestion_ok"],
        "market_structure":aligned if REQUIRE_MARKET_ALIGNMENT else True,
        "swing_sr":sr["sr_touch"] if REQUIRE_SWING_SR_TOUCH else True,
        "volume":volume["volume_ok"] if REQUIRE_VOLUME else True,
        "daily_range":day["daily_range_ok"] if REQUIRE_DAILY_RANGE else True,
        "higher_timeframe":htf["htf_ok"] if REQUIRE_HTF else True,
        "liquidity":liquidity["liquidity_area_ok"] if REQUIRE_LIQUIDITY_AREA else True,
    }
    failures=[k for k,passed in checks.items() if not passed]
    return {**core,**metrics,
            "market_structure":structure["market_structure"],
            "sr_reference":sr["sr_reference"],"sr_lines":str(sr["sr_lines"]),
            **volume,**wicks,**day,**htf,**liquidity,
            **{"pass_"+k:v for k,v in checks.items()},
            "decision":"GOOD" if not failures else "WAIT",
            "reason":";".join(failures),
            "_c1_i":c1_i,"_c2_i":c2_i,"_c3_i":c3_i}


def scan(bars):
    """Print first CORE-TRUE detections, then evaluate quality and structure.

    Finds the earliest C3 confirmed by CLOSE for each consecutive C1/C2
    sweep and direction. BUY/SELL states are independent. Missing 15m bars
    break the candidate. Unconfirmed patterns are NOT plotted as candidates.
    """
    result=[]
    for c2_i in range(1,len(bars)-1):
        c1_i=c2_i-1
        if bars[c2_i].ts-bars[c1_i].ts!=timedelta(minutes=15):
            continue
        for side in ("BUY","SELL"):
            for c3_i in range(c2_i+1,min(len(bars),c2_i+LOOK_AHEAD_C3_BARS+1)):
                if bars[c3_i].ts-bars[c3_i-1].ts!=timedelta(minutes=15):
                    break
                core=candle_detect_core(bars,c1_i,c2_i,c3_i,side)
                if core is not None:
                    result.append(evaluate_pipeline(bars,c1_i,c2_i,c3_i,core))
                    break
                # Stop waiting if C2 was invalidated; do not resurrect later.
                c2,c3=bars[c2_i],bars[c3_i]
                if side=="BUY" and c3.l<c2.l or side=="SELL" and c3.h>c2.h:
                    break
    return result


def plot_candidates(bars,rows,outpath,title):
    """Maintain earlier dark candle design: C2 yellow, entry blue, SL red.

    One chart for EACH requested candidate, collected into one multipage PDF.
    Entry/SL/TP are reference drawings from next 5m/15m candidate context,
    NOT a 5-minute execution backtest; no hypothetical P/L is claimed.
    """
    if not rows:
        print("No "+title+" to plot.")
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.patches import Rectangle
    except ImportError as e:
        raise SystemExit("Plotting needs matplotlib: pip install matplotlib") from e
    outpath.parent.mkdir(parents=True,exist_ok=True)
    with PdfPages(outpath) as pdf:
        for row in rows:
            i=row["_c3_i"]; c1=row["_c1_i"]; c2=row["_c2_i"]
            start=max(0,i-CANDLE_LOOKBACK)
            end=min(len(bars),i+CANDLE_LOOKFORWARD+1)
            candles=bars[start:end]
            # Never connect across a session break; one local chart only.
            fig,ax=plt.subplots(figsize=(10,4),facecolor="#10151d")
            ax.set_facecolor("#10151d")
            for j,c in enumerate(candles):
                col="#22c69d" if c.c>=c.o else "#e56d71"
                ax.plot([j,j],[c.l,c.h],color=col,lw=1.35)
                ax.add_patch(Rectangle((j-.28,min(c.o,c.c)),.56,max(.15,abs(c.c-c.o)),
                                       facecolor=col,edgecolor=col))
                global_i=start+j
                if global_i==c2:
                    ax.axvspan(j-.45,j+.45,color="#eab308",alpha=.15)
                if global_i in (c1,c2,i):
                    ax.text(j,c.h+.6,{c1:"C1",c2:"C2",i:"C3"}[global_i],
                            fontsize=9,weight="bold",ha="center",color="#eab308")
            # Entry is next 15m opening estimate; may differ from 5m next-open
            # around gaps. This is deliberately NOT represented as an actual fill.
            entry=bars[i].c
            stop=entry+(-REFERENCE_STOP_POINTS if row["side"]=="BUY" else REFERENCE_STOP_POINTS)
            tp=entry+(REFERENCE_TARGET_POINTS if row["side"]=="BUY" else -REFERENCE_TARGET_POINTS)
            ax.axhline(entry,color="#60a5fa",ls="--",lw=1,label=f"Ref entry {entry:.2f}")
            ax.axhline(stop,color="#f87171",ls="--",lw=1,label=f"Ref SL {stop:.2f}")
            ax.axhline(tp,color="#c084fc",ls=":",lw=1,label=f"Ref TP {tp:.2f}")
            ticks=list(range(0,len(candles),2))
            ax.set_xticks(ticks,[candles[j].ts.astimezone(base.UK).strftime("%H:%M") for j in ticks])
            ax.tick_params(colors="#b5c1d0",labelsize=9)
            for sp in ax.spines.values():sp.set_color("#344153")
            ax.grid(alpha=.12,color="#b5c1d0")
            ax.set_title(f'MES | {row["side"]} | {row["c3_uk"]} | {row["decision"]} | '
                         f'wick {row["c2_wick_body"]:.2f}x | sweep {row["sweep_points"]:.2f}pt',
                         color="white",fontsize=11,loc="left")
            ax.legend(loc="upper left",fontsize=8,facecolor="#1c2432",labelcolor="white")
            fig.text(.11,.02,"Structure: "+row["market_structure"]+"   |   Reason: "+
                     (row["reason"] or "all checks pass"),color="#c0cad8",fontsize=9)
            fig.subplots_adjust(bottom=.18,top=.88)
            pdf.savefig(fig,facecolor=fig.get_facecolor())
            plt.close(fig)
    print(f"{title}: {len(rows)} panels -> {outpath}")


def write_csv(rows,path):
    """Audit file contains all stage values, check outcomes and WAIT reasons."""
    path.parent.mkdir(parents=True,exist_ok=True)
    public=[{k:v for k,v in row.items() if not k.startswith("_")} for row in rows]
    if not public:
        print("No CORE-TRUE candidates; no CSV written.")
        return
    with path.open("w",newline="",encoding="utf-8") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(public[0]))
        writer.writeheader();writer.writerows(public)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date",help="UK date YYYY-MM-DD")
    p.add_argument("--plot-all",action="store_true",help="plot every CORE-TRUE candidate")
    p.add_argument("--plot-good",action="store_true",help="plot only GOOD (all required checks pass)")
    p.add_argument("--plot-both",action="store_true",help="output both chart collections")
    p.add_argument("--show-wait",action="store_true",help="print rejection reasons as well")
    p.add_argument("--output-dir",default=str(ROOT/"results"/"MES_relax_v1_review"))
    args=p.parse_args()
    bars=base.to_15m(base.read_ibkr_5m(base.SOURCES))
    if not bars:
        raise SystemExit("No complete IBKR 15m bars loaded.")
    found=scan(bars)
    if args.date:
        found=[x for x in found if x["c3_uk"].startswith(args.date)]
    good=[x for x in found if x["decision"]=="GOOD"]
    print("CORE-TRUE:",len(found),"GOOD:",len(good),"WAIT:",len(found)-len(good))
    for x in found:
        if x["decision"]=="GOOD" or args.show_wait:
            print(f'{x["c3_uk"]} {x["side"]:4s} CORE=True | '
                  f'structure={x["market_structure"]} | '
                  f'sweep={x["sweep_points"]:.2f} | wick={x["c2_wick_body"]:.2f}x | '
                  f'last5={x["last5_long_wicks"]} | {x["decision"]} {x["reason"]}')
    dest=Path(args.output_dir)
    label=args.date or "all_dates"
    write_csv(found,dest/f"MES_{label}_all_core_candidates.csv")
    if args.plot_all or args.plot_both:
        plot_candidates(bars,found,dest/f"MES_{label}_ALL_CANDIDATES.pdf","ALL CORE-TRUE")
    if args.plot_good or args.plot_both:
        plot_candidates(bars,good,dest/f"MES_{label}_GOOD_CANDIDATES.pdf","GOOD CANDIDATES")
    print("NOTE: This scanner classifies signals; plots are references, NOT backtested P/L.")


if __name__=="__main__":
    main()
