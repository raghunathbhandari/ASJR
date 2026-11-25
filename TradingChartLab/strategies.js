/* ASJR Trading Chart Lab — persistent strategy registry.
   New research implementations register with id, name, status, description and run(bars,params).
   Draft names added in the UI are only labels, not backtested strategies. */
"use strict";
window.ASJR_STRATEGIES = [
  {
    id: "vwap-mean-reversion",
    name: "VWAP Mean Reversion",
    status: "active",
    description: "Long-only: buy a confirmed rebound from below session VWAP; target frozen entry-signal VWAP.",
    run: function(bars, params) {
      const deviation=Number(params.deviation), stop=Number(params.stop), maxHold=Number(params.hold);
      const trades=[]; let position=null;
      for(let i=2;i<bars.length;i++){
        const b=bars[i], p=bars[i-1], pp=bars[i-2];
        const lastInSession = (j)=>j===bars.length-1 || bars[j].session!==bars[j+1].session;
        if(position){
          let reason=null, exit=null;
          // Conservative OHLC sequencing: when target and stop are both touched in a bar, count STOP first.
          if(b.open<=position.stop){reason="STOP";exit=b.open;}
          else if(b.low<=position.stop){reason="STOP";exit=position.stop;}
          else if(b.high>=position.target){reason="VWAP";exit=position.target;}
          else if(lastInSession(i)){reason="SESSION";exit=b.close;}
          else if(i-position.entryIndex>=maxHold){reason="TIME";exit=b.close;}
          if(reason){
            position.exitIndex=i;position.exit=exit;position.reason=reason;
            position.points=Math.round((exit-position.entry)*4)/4;
            trades.push(position); position=null;
            continue; // No instantaneous re-entry on exit candle.
          }
        }
        if(!position && b.session===p.session && p.session===pp.session && !lastInSession(i)
          && p.low<=p.vwap-deviation && p.close>p.open && p.close>pp.close
          && p.close<p.vwap-4 && b.open<p.vwap-2){
          const target=Math.floor(p.vwap*4)/4; // MES tick-size rounding.
          if(target>b.open+2){
            position={entryIndex:i, entry:b.open, signalIndex:i-1, session:b.session,
              stop:b.open-stop, target, exitIndex:null, reason:null};
          }
        }
      }
      if(position){
        const i=bars.length-1;
        position.exitIndex=i;position.exit=bars[i].close;position.reason="DATA_END";
        position.points=Math.round((position.exit-position.entry)*4)/4;
        trades.push(position);
      }
      return trades;
    }
  },
  {id:"algo-with-renko",name:"AlgoWithRenko · 20pt",status:"planned",description:"Existing ASJR Renko strategy; chart overlay/backtest integration planned. Rules remain in AlgoWithRenko/README.md.",source:"../AlgoWithRenko/README.md"},
  {id:"vwap-ema9",name:"VWAP + EMA9",status:"planned",description:"VWAP and moving-average trend-following strategy; implementation pending.",source:"../Backtesting/VWAP_EMA9/"},
  {id:"three-candle",name:"Three-Candle Reversal",status:"planned",description:"Three-candle reversal detector and backtest overlays; implementation pending.",source:"../three_candle/"},
  {id:"gann-date-360",name:"Gann Date 360",status:"planned",description:"Date-cycle research overlay; implementation pending."},
  {id:"point-figure",name:"Point & Figure",status:"planned",description:"Point-and-figure noise-reduction and signal research; implementation pending."}
];
