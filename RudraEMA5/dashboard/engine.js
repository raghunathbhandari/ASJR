/* RudraEMA5 Research Engine v3 — historical OHLC replay only, no order routing.
   Frozen comparison parameters: EMA5 slope <= -0.15%/3 bars; complete C1 < EMA5;
   swing from max high of prior 24 completed bars to C1 low >=2%;
   Wilder RSI14(C1) <36; V3 ALSO requires RSI(C1)>RSI(previous 5m candle).
   C2 trigger max(ceil_cent(C1 close*1.002),ceil_cent(C1 high+0.02)).
   Stop -1%, +1% price activates 0.2% high-water trailing stop. One position
   per Europe/London date, marked out at last available bar of that date.
   C2 range-low filter is REMOVED. Data is *not* an executable-tick backtest. */
(function(root){
"use strict";
const UTC_START=Date.UTC(2026,8,1);
const ukFmt=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"});
function ukLabels(ts){const o={};for(const p of ukFmt.formatToParts(new Date(ts)))if(p.type!=="literal")o[p.type]=p.value;return{day:o.year+"-"+o.month+"-"+o.day,clock:o.hour+":"+o.minute}}
function decode(compact){return compact.map(a=>{const ts=UTC_START+a[0]*60000,uk=ukLabels(ts);return {ts,o:a[1]/10000,h:a[2]/10000,l:a[3]/10000,c:a[4]/10000,v:a[5],day:uk.day,clock:uk.clock}})}
function aggregate(native,minutes){
 if(minutes===5)return native.map(x=>({...x}));
 const groups=[];let group=null;
 for(const b of native){const t=Math.floor(b.ts/(minutes*60000))*minutes*60000;if(!group||group.ts!==t){group={ts:t,items:[]};groups.push(group)}group.items.push(b)}
 const count=minutes/5;
 return groups.filter(g=>g.items.length===count&&g.items[0].ts===g.ts&&g.items.every((x,i)=>!i||x.ts-g.items[i-1].ts===300000)).map(g=>{const x=g.items,uk=ukLabels(g.ts);return {ts:g.ts,o:x[0].o,h:Math.max(...x.map(y=>y.h)),l:Math.min(...x.map(y=>y.l)),c:x.at(-1).c,v:x.reduce((s,b)=>s+b.v,0),day:uk.day,clock:uk.clock}});
}
function indicators(bars){let ema=null,ag=0,al=0;for(let i=0;i<bars.length;i++){const b=bars[i];ema=ema===null?b.c:(b.c+2*ema)/3;b.ema=ema;b.rsi=null;if(!i)continue;const diff=b.c-bars[i-1].c,g=Math.max(0,diff),l=Math.max(0,-diff);if(i<=14){ag+=g;al+=l;if(i<14)continue;ag/=14;al/=14}else{ag=(13*ag+g)/14;al=(13*al+l)/14}b.rsi=al?100-100/(1+ag/al):(ag?100:50)}return bars}
const ceil=n=>Math.ceil((n-1e-9)*100)/100;
const options=opts=>({timeframe:5,version:"V3",rsi:36,swing:2,slope:.15,stop:1,trail:.2,...opts});
function replay(bars,userOptions={}){
 const o=options(userOptions);const days=[...new Set(bars.map(b=>b.day))],byDay=[],allTrades=[];
 for(const day of days){
  let tr=[],cand=[],pos=null,eligible=0,swingCount=0,rsiCount=0;
  const first=bars.findIndex(b=>b.day===day),dayBars=bars.filter(b=>b.day===day),last=first+dayBars.length-1;
  function exit(b,j,p,reason){
   const result={day,c1:pos.c1,entryTime:pos.entryTime,exitTime:b.ts,entryIndex:pos.entryIndex,exitIndex:j,c1Index:pos.c1Index,entry:pos.entry,exit:p,R:100*(p/pos.entry-1),rsi:pos.rsi,priorRsi:pos.priorRsi,swing:pos.swing,initialStop:pos.initialStop,reason,stops:pos.stops,armed:pos.armed};
   tr.push(result);pos=null;
  }
  for(let i=Math.max(first,25);i<=last;i++){
   const b=bars[i];
   if(pos){
    if(b.o<=pos.stop){pos.stops.push({i,v:pos.stop});exit(b,i,b.o,"Gap through stop");continue}
    if(b.l<=pos.stop){pos.stops.push({i,v:pos.stop});exit(b,i,pos.stop,pos.armed?"Trailing stop":"Initial stop");continue}
    if(!pos.armed&&b.h>=pos.entry*(1+o.stop/100)){pos.armed=true;pos.peak=b.h}
    if(pos.armed){pos.peak=Math.max(pos.peak,b.h);let newStop=Math.max(pos.stop,pos.peak*(1-o.trail/100));pos.stops.push({i,v:newStop});
      if(b.c<=newStop){exit(b,i,newStop,"Same-bar trail (close confirmation)");continue}
      pos.stop=newStop;
    }else pos.stops.push({i,v:pos.stop});
    continue;
   }
   const c1=bars[i-1],prev=bars[i-4],prevC1=bars[i-2];
   const delta=o.timeframe*60000;
   if(b.ts-c1.ts!==delta||c1.ts-prev.ts!==3*delta)continue;
   if(c1.h>=c1.ema||100*(c1.ema/prev.ema-1)>-o.slope)continue;
   eligible++;
   let highest=-Infinity;for(let j=i-25;j<i-1;j++)highest=Math.max(highest,bars[j].h);
   const swing=100*(highest-c1.l)/highest;
   if(swing<o.swing)continue;swingCount++;
   if(c1.rsi===null||c1.rsi>=o.rsi||(o.version==="V3"&&!(c1.rsi>prevC1.rsi)))continue;rsiCount++;
   const threshold=Math.max(ceil(c1.h+.02),ceil(c1.c*1.002));
   cand.push({i:i-1,time:c1.ts,rsi:c1.rsi,priorRsi:prevC1.rsi,swing,threshold,breakout:b.h>=threshold});
   if(b.h<threshold)continue;
   const entry=Math.max(b.o,threshold);
   pos={c1:c1.ts,c1Index:i-1,entryIndex:i,entryTime:b.ts,entry,rsi:c1.rsi,priorRsi:prevC1.rsi,swing,initialStop:entry*.99,stop:entry*.99,peak:entry,armed:false,stops:[{i,v:entry*.99}]};
   if(b.l<=pos.stop){exit(b,i,pos.stop,"Entry-bar stop-first (ambiguous)");continue}
   if(b.h>=entry*1.01){pos.armed=true;pos.peak=b.h;const ns=Math.max(pos.stop,b.h*(1-o.trail/100));pos.stops.push({i,v:ns});if(b.c<=ns){exit(b,i,ns,"Entry-bar trail (close confirmation)");continue}pos.stop=ns}
  }
  if(pos&&dayBars.length)exit(bars[last],last,bars[last].c,"UK day-end mark-to-market");
  allTrades.push(...tr);
  byDay.push({date:day,candles:dayBars.length,first:dayBars[0]?.ts||null,last:dayBars.at(-1)?.ts||null,c1Count:eligible,swingCount,rsiCount,setups:cand,trades:tr,wins:tr.filter(x=>x.R>0).length,losses:tr.filter(x=>x.R<0).length,sumR:tr.reduce((s,x)=>s+x.R,0)});
 }
 const gains=allTrades.filter(x=>x.R>0).reduce((s,t)=>s+t.R,0),loss=-allTrades.filter(x=>x.R<0).reduce((s,t)=>s+t.R,0);
 return {options:o,byDay,trades:allTrades,summary:{trades:allTrades.length,wins:allTrades.filter(t=>t.R>0).length,losses:allTrades.filter(t=>t.R<0).length,sumR:allTrades.reduce((s,t)=>s+t.R,0),winRate:allTrades.length?100*allTrades.filter(t=>t.R>0).length/allTrades.length:null,profitFactor:loss?gains/loss:null}};
}
root.RudraEMA5Engine={decode,aggregate,indicators,replay,ukLabels,ceil,epoch:UTC_START};
})(window);
