/* ASJR Trading Chart Lab — v1.0
 * Source: three_candle/data/MESZ2026_IBKR_5m_2026-10.csv (IBKR)
 * Canvas render, no external libraries. No broker connections or orders.
 */
"use strict";
(function(){
  const ROOT="https://raw.githubusercontent.com/raghunathbhandari/ASJR/main/";
  const DATASET={
    id:"mes-oct-2026",
    path:"three_candle/data/MESZ2026_IBKR_5m_2026-10.csv",
    label:"MESZ2026 · October 2026"
  };
  const $=id=>document.getElementById(id);
  const refs={
    canvas:$("chart"),wrap:$("chart-wrap"),tooltip:$("tooltip"),
    dataset:$("dataset"),focus:$("focus"),session:$("session"),
    status:$("data-status"),caption:$("range-caption"),strategyList:$("strategy-list"),
    activeTitle:$("active-title"),activeDescription:$("active-description"),
    tradeBody:$("trades-body"),tradeCaption:$("trade-caption"),
    showVwap:$("show-vwap"),showEma9:$("show-ema9"),showEma20:$("show-ema20"),
    showTrades:$("show-trades"),showCandles:$("show-candles")
  };
  const state={
    bars:[],sessions:[],trades:[],strategyId:"vwap-mean-reversion",
    customStrategies:[],start:0,end:0,hover:null,drag:null,selectedTrade:null,
    chart:{left:67,right:20,top:30,bottom:39,width:0,height:0,pMin:0,pMax:0}
  };
  const fmt=(v,d=2)=>Number(v).toLocaleString("en-GB",{minimumFractionDigits:d,maximumFractionDigits:d});
  const ukTime=ms=>new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/London",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",hour12:false}).format(new Date(ms))+" UK";
  const utcTime=ms=>new Date(ms).toISOString().slice(5,16).replace("T"," ")+" UTC";
  const statusMap={STOP:"Stop-loss",VWAP:"VWAP target",TIME:"4h time exit",SESSION:"Session close",DATA_END:"End of data"};
  const number=(id,fallback)=>{const v=Number($(id).value);return Number.isFinite(v)&&v>0?v:fallback};
  function setText(id,value){$(id).textContent=value;}
  function node(tag,cls,txt){
    const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n;
  }
  function registry(){
    return [...window.ASJR_STRATEGIES,...state.customStrategies.map(name=>({
      id:"draft-"+name.toLowerCase().replace(/[^a-z0-9]+/g,"-"),
      name,status:"draft",description:"Draft name saved locally. No trading rules implemented."
    }))];
  }
  function selectedStrategy(){return registry().find(x=>x.id===state.strategyId)||window.ASJR_STRATEGIES[0];}
  function loadNames(){
    try{const a=JSON.parse(localStorage.getItem("asjr-chartlab-strategy-names-v1")||"[]");
      state.customStrategies=Array.isArray(a)?a.filter(s=>typeof s==="string"&&s.length<61).slice(0,60):[];
    }catch(_){state.customStrategies=[];}
  }
  function renderStrategyList(){
    refs.strategyList.replaceChildren();
    setText("strategy-count",String(registry().length));
    registry().forEach(s=>{
      const button=node("button","strategy-item"+(s.id===state.strategyId?" selected":""),"");
      button.type="button";
      const top=node("div","strategy-top");
      top.append(node("span","strategy-name",s.name),node("span","status "+s.status,s.status==="active"?"Active":s.status==="planned"?"Planned":"Draft"));
      button.append(top,node("div","strategy-desc",s.description));
      button.addEventListener("click",()=>{state.strategyId=s.id;renderStrategyList();recalculate();});
      refs.strategyList.append(button);
    });
    const current=selectedStrategy();
    refs.activeTitle.textContent=current.name;
    refs.activeDescription.textContent=current.description;
    document.querySelector(".parameters").hidden=current.status!=="active";
  }
  function readCsv(text){
    const lines=text.trim().split(/\r?\n/);
    if(!lines.length||!lines[0].includes("Datetime_UTC"))throw Error("Unexpected CSV header.");
    const fields=lines[0].split(",");
    const col=key=>fields.indexOf(key);
    const c={t:col("Datetime_UTC"),open:col("Open"),high:col("High"),low:col("Low"),close:col("Close"),volume:col("Volume")};
    if(Object.values(c).some(i=>i<0))throw Error("CSV must contain UTC timestamp, OHLC and Volume.");
    const rows=[];
    for(let k=1;k<lines.length;k++){
      const a=lines[k].split(",");
      const ms=Date.parse((a[c.t]||"").replace(" ","T"));
      const b={t:ms,open:Number(a[c.open]),high:Number(a[c.high]),low:Number(a[c.low]),close:Number(a[c.close]),volume:Number(a[c.volume])};
      if(!Number.isFinite(b.t)||!Object.values(b).every(Number.isFinite)||b.volume<0)throw Error("Bad OHLCV input at CSV line "+(k+1));
      rows.push(b);
    }
    rows.sort((a,b)=>a.t-b.t);
    if(rows.some((b,i)=>i>0&&b.t===rows[i-1].t))throw Error("Duplicate timestamps in MES CSV.");
    return rows;
  }
  function sessionKey(ms){
    // CME equity-index Globex session begins 17:00 America/Chicago (22:00 UTC in October 2026).
    // The 00:00–21:59 UTC bars belong to the current session date; 22:00+ to the next.
    const d=new Date(ms);return new Date(ms+(d.getUTCHours()>=22?86400000:0)).toISOString().slice(0,10);
  }
  function makeBars(five){
    const bars=[];let session="",volume=0,totalPV=0,last=null;
    for(const b of five){
      const key=sessionKey(b.t);
      if(key!==session){session=key;volume=0;totalPV=0;}
      const typical=(b.high+b.low+b.close)/3;
      totalPV+=typical*b.volume;volume+=b.volume;
      const t=Math.floor(b.t/900000)*900000;
      if(!last||last.t!==t){
        last={t,session:key,open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume,vwap:volume?totalPV/volume:typical,count:1};
        bars.push(last);
      }else{
        last.high=Math.max(last.high,b.high);
        last.low=Math.min(last.low,b.low);
        last.close=b.close;last.volume+=b.volume;last.count++;
        last.vwap=volume?totalPV/volume:typical;
      }
    }
    if(bars.some(b=>b.count!==3))throw Error("Incomplete 15-minute candles in the source; inspect missing data before testing.");
    let e9=null,e20=null;
    for(const b of bars){
      e9=e9===null?b.close:e9+(2/10)*(b.close-e9);
      e20=e20===null?b.close:e20+(2/21)*(b.close-e20);
      b.ema9=e9;b.ema20=e20;
    }
    return bars;
  }
  function makeSessions(bars){
    const out=[];
    for(let i=0;i<bars.length;i++){
      const b=bars[i];
      if(!out.length||out[out.length-1].key!==b.session)out.push({key:b.session,start:i,end:i+1});
      else out[out.length-1].end=i+1;
    }
    return out;
  }
  function populateSessions(){
    refs.session.replaceChildren();
    state.sessions.forEach((s,i)=>{
      const item=node("option",null,"Oct "+s.key.slice(-2)+", "+s.key.slice(0,4));
      item.value=String(i);refs.session.append(item);
    });
    refs.session.value=String(Math.min(5,state.sessions.length-1));
  }
  function setRange(a,b,custom=false){
    if(!state.bars.length)return;
    const n=state.bars.length, span=Math.max(12,Math.min(n,Math.round(b-a)));
    a=Math.max(0,Math.min(n-span,Math.round(a)));
    state.start=a;state.end=a+span;
    if(custom)refs.focus.value="custom";
    updateFocusDetails();render();
  }
  function focusOnSelection(){
    const s=state.sessions;
    if(!s.length)return;
    const i=Math.max(0,Math.min(s.length-1,Number(refs.session.value)||0));
    const mode=refs.focus.value;
    if(mode==="all")setRange(0,state.bars.length);
    else if(mode==="6h")setRange(s[i].start,Math.min(s[i].end,s[i].start+24));
    else{
      const num=mode==="3"?3:mode==="5"?5:1;
      const j=Math.min(s.length-1,i+num-1);
      setRange(s[i].start,s[j].end);
    }
  }
  function updateFocusDetails(){
    const a=state.bars[state.start],b=state.bars[state.end-1];
    if(!a||!b)return;
    refs.caption.textContent=utcTime(a.t)+" — "+utcTime(b.t)+" · completed 15-minute bars · hover for UK time";
    const entries=state.trades.filter(t=>t.entryIndex>=state.start&&t.entryIndex<state.end);
    const pts=entries.reduce((v,t)=>v+t.points,0);
    refs.tradeCaption.textContent=entries.length+" entries in chart range · "+(pts>=0?"+":"")+fmt(pts)+" gross MES points";
  }
  function recalculate(){
    const strategy=selectedStrategy();
    if(state.bars.length&&typeof strategy.run==="function"){
      state.trades=strategy.run(state.bars,{deviation:number("deviation",15),stop:number("stop",20),hold:number("hold",16)});
    }else state.trades=[];
    renderSummary();renderTrades();updateFocusDetails();render();
  }
  function renderSummary(){
    const t=state.trades,strategy=selectedStrategy();
    if(strategy.status!=="active"){
      ["metric-trades","metric-winrate","metric-points","metric-drawdown"].forEach(x=>setText(x,"—"));
      setText("metric-dollars","Strategy not implemented");
      return;
    }
    const net=t.reduce((a,b)=>a+b.points,0);
    const winners=t.filter(x=>x.points>0).length;
    let eq=0,peak=0,maxDD=0;
    for(const x of t){eq+=x.points;peak=Math.max(peak,eq);maxDD=Math.max(maxDD,peak-eq);}
    setText("metric-trades",String(t.length));
    setText("metric-winrate",t.length?fmt(100*winners/t.length,1)+"%":"—");
    setText("metric-points",(net>0?"+":"")+fmt(net)+" pts");
    $("metric-points").className=net>=0?"positive":"negative";
    setText("metric-dollars",(net>=0?"+":"")+fmt(net*5)+" USD gross · 1 MES");
    setText("metric-drawdown",fmt(maxDD)+" pts");
    setText("rule-explanation",
      "BUY: preceding completed 15m bar reaches "+fmt(number("deviation",15))+
      " pts below VWAP, closes bullish and improving but remains 4+ pts below VWAP; enter next bar OPEN while still 2+ pts below VWAP. "+
      "Target: previous bar VWAP frozen at signal (rounded down to 0.25). Stop: "+fmt(number("stop",20))+
      " pts. EXIT: stop first, VWAP target, session close, or "+number("hold",16)+
      " bars. 1 MES = $5/point. Same-bar stop/target uses pessimistic stop-first assumptions; fees and slippage excluded.");
  }
  function renderTrades(){
    refs.tradeBody.replaceChildren();
    const filtered=state.trades.filter(t=>t.entryIndex>=state.start&&t.entryIndex<state.end);
    if(!filtered.length){
      const tr=node("tr"),td=node("td",null,selectedStrategy().status==="active"?"No BUY entries in this focus window.":"Select an active strategy to see simulated trades.");
      td.colSpan=7;tr.append(td);refs.tradeBody.append(tr);return;
    }
    for(const t of filtered){
      const tr=node("tr",state.selectedTrade===t?"selected":"");
      const values=[t.session,ukTime(state.bars[t.entryIndex].t),fmt(t.entry),fmt(t.exit),statusMap[t.reason]||t.reason,
        (t.points>0?"+":"")+fmt(t.points),(t.points>0?"+":"")+fmt(t.points*5)];
      values.forEach((value,i)=>{const td=node("td",i>=5?(t.points>=0?"positive":"negative"):"",value);tr.append(td);});
      tr.style.cursor="pointer";tr.title="Click to focus this trade";
      tr.addEventListener("click",()=>{state.selectedTrade=t;setRange(t.entryIndex-14,t.exitIndex+15,true);});
      refs.tradeBody.append(tr);
    }
  }
  function resize(){
    const w=refs.wrap.clientWidth,h=refs.wrap.clientHeight,dpr=Math.min(2,window.devicePixelRatio||1);
    if(!w||!h)return;
    refs.canvas.width=Math.round(w*dpr);refs.canvas.height=Math.round(h*dpr);
    refs.canvas.style.width=w+"px";refs.canvas.style.height=h+"px";
    const ctx=refs.canvas.getContext("2d");
    ctx.setTransform(dpr,0,0,dpr,0,0);
    state.chart.width=w;state.chart.height=h;
    render();
  }
  function plotGeometry(){
    const q=state.chart;
    q.left=66;q.right=18;q.top=24;q.bottom=42;
    q.plotWidth=Math.max(10,q.width-q.left-q.right);
    q.plotHeight=Math.max(10,q.height-q.top-q.bottom);
    const sample=state.bars.slice(state.start,state.end);
    const all=[];
    for(const b of sample){
      all.push(b.high,b.low);
      if(refs.showVwap.checked)all.push(b.vwap);
      if(refs.showEma9.checked)all.push(b.ema9);
      if(refs.showEma20.checked)all.push(b.ema20);
    }
    const low=Math.min(...all),high=Math.max(...all),margin=Math.max(6,(high-low)*.08);
    q.pMin=Math.floor((low-margin)/5)*5;q.pMax=Math.ceil((high+margin)/5)*5;
    q.x=i=>q.left+(i-state.start)/Math.max(1,state.end-state.start-1)*q.plotWidth;
    q.y=v=>q.top+(q.pMax-v)/(q.pMax-q.pMin)*q.plotHeight;
    return q;
  }
  function render(){
    if(!state.bars.length||!state.chart.width)return;
    const ctx=refs.canvas.getContext("2d"),q=plotGeometry(),bars=state.bars;
    ctx.clearRect(0,0,q.width,q.height);
    ctx.fillStyle="#0e151e";ctx.fillRect(q.left,q.top,q.plotWidth,q.plotHeight);
    ctx.font="11px system-ui, sans-serif";ctx.textBaseline="middle";
    for(let i=0;i<=5;i++){
      const y=q.top+q.plotHeight*i/5,p=q.pMax-(q.pMax-q.pMin)*i/5;
      ctx.strokeStyle="#273545";ctx.setLineDash([3,5]);ctx.beginPath();ctx.moveTo(q.left,y);ctx.lineTo(q.width-q.right,y);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle="#aabbd0";ctx.textAlign="right";ctx.fillText(fmt(p,0),q.left-8,y);
    }
    for(let i=0;i<=5;i++){
      const j=Math.min(state.end-1,state.start+Math.floor((state.end-state.start-1)*i/5));
      const x=q.x(j);ctx.strokeStyle="#1b2938";ctx.beginPath();ctx.moveTo(x,q.top);ctx.lineTo(x,q.top+q.plotHeight);ctx.stroke();
      const longWindow=state.end-state.start>100;
      const label=longWindow?utcTime(bars[j].t).slice(0,6):utcTime(bars[j].t).slice(7,12);
      ctx.fillStyle="#9dafc3";ctx.textAlign="center";ctx.fillText(label,x,q.height-20);
    }
    for(const s of state.sessions){
      if(s.start<=state.start||s.start>=state.end)continue;
      ctx.strokeStyle="#607288";ctx.setLineDash([2,7]);ctx.beginPath();ctx.moveTo(q.x(s.start),q.top);ctx.lineTo(q.x(s.start),q.top+q.plotHeight);ctx.stroke();ctx.setLineDash([]);
    }
    function drawLine(key,color,width,segmented){
      ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin="round";ctx.lineCap="round";
      ctx.beginPath();
      for(let i=state.start;i<state.end;i++){
        const b=bars[i],x=q.x(i),y=q.y(b[key]);
        if(i===state.start||(segmented&&b.session!==bars[i-1].session))ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.stroke();
    }
    if(refs.showVwap.checked)drawLine("vwap","#e4ac35",2.5,true);
    if(refs.showEma9.checked)drawLine("ema9","#ca85f6",1.6,false);
    if(refs.showEma20.checked)drawLine("ema20","#46c1b4",1.6,false);
    if(refs.showCandles.checked && (q.plotWidth/(state.end-state.start))>=3){
      const candleWidth=Math.max(1,Math.min(8,q.plotWidth/(state.end-state.start)*.66));
      for(let i=state.start;i<state.end;i++){
        const b=bars[i],x=q.x(i),up=b.close>=b.open;
        ctx.strokeStyle=up?"#40bc91":"#e86f76";ctx.fillStyle=ctx.strokeStyle;
        ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,q.y(b.high));ctx.lineTo(x,q.y(b.low));ctx.stroke();
        ctx.fillRect(x-candleWidth/2,Math.min(q.y(b.open),q.y(b.close)),candleWidth,Math.max(1,Math.abs(q.y(b.close)-q.y(b.open))));
      }
    }else drawLine("close","#4e9cff",1.9,false);
    if(refs.showCandles.checked && (q.plotWidth/(state.end-state.start))>=3){
      // Candles replace the price line only in sufficiently zoomed-in windows.
    }
    if(refs.showTrades.checked){
      for(const t of state.trades){
        const ent=t.entryIndex>=state.start&&t.entryIndex<state.end;
        const ex=t.exitIndex>=state.start&&t.exitIndex<state.end;
        if(ent&&ex){
          ctx.strokeStyle=t.points>=0?"#459c7b66":"#d45c6366";ctx.lineWidth=1.4;ctx.setLineDash([4,3]);
          ctx.beginPath();ctx.moveTo(q.x(t.entryIndex),q.y(t.entry));ctx.lineTo(q.x(t.exitIndex),q.y(t.exit));ctx.stroke();ctx.setLineDash([]);
        }
        if(ent){
          const x=q.x(t.entryIndex),y=q.y(t.entry);
          ctx.fillStyle="#38c88c";ctx.strokeStyle="#d3f7e3";ctx.lineWidth=1;
          ctx.beginPath();ctx.moveTo(x,y-8);ctx.lineTo(x-6,y+5);ctx.lineTo(x+6,y+5);ctx.closePath();ctx.fill();ctx.stroke();
        }
        if(ex){
          const x=q.x(t.exitIndex),y=q.y(t.exit);
          ctx.fillStyle=t.reason==="VWAP"?"#efb93c":"#ed7176";
          ctx.strokeStyle="#eaf2ff";ctx.lineWidth=1;ctx.beginPath();ctx.arc(x,y,4.7,0,Math.PI*2);ctx.fill();ctx.stroke();
        }
      }
    }
    if(Number.isInteger(state.hover)&&state.hover>=state.start&&state.hover<state.end){
      const x=q.x(state.hover),y=q.y(bars[state.hover].close);
      ctx.setLineDash([3,4]);ctx.strokeStyle="#b0c4e0aa";ctx.beginPath();ctx.moveTo(x,q.top);ctx.lineTo(x,q.top+q.plotHeight);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle="#e6f2ff";ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();
    }
  }
  function posX(event){return event.clientX-refs.wrap.getBoundingClientRect().left;}
  function indexAt(x){
    const q=state.chart,clamped=Math.max(0,Math.min(1,(x-q.left)/q.plotWidth));
    return Math.max(state.start,Math.min(state.end-1,Math.round(state.start+clamped*(state.end-state.start-1))));
  }
  function showTooltip(event){
    const x=posX(event);
    if(x<state.chart.left||x>state.chart.width-state.chart.right){refs.tooltip.hidden=true;state.hover=null;render();return;}
    const i=indexAt(x),b=state.bars[i];state.hover=i;
    const notes=state.trades.filter(t=>t.entryIndex===i||t.exitIndex===i).map(t=>t.entryIndex===i?
      "▲ BUY "+fmt(t.entry):"● "+(statusMap[t.reason]||t.reason)+" "+fmt(t.exit)+" ("+(t.points>0?"+":"")+fmt(t.points)+" pts)");
    refs.tooltip.textContent=ukTime(b.t)+"\nClose "+fmt(b.close)+"\nVWAP "+fmt(b.vwap)+"\nDifference "+fmt(b.close-b.vwap)+" pts"+
      (refs.showEma9.checked?"\nEMA9 "+fmt(b.ema9):"")+
      (refs.showEma20.checked?"\nEMA20 "+fmt(b.ema20):"")+
      (notes.length?"\n"+notes.join("\n"):"");
    refs.tooltip.style.whiteSpace="pre-line";
    const left=Math.max(5,Math.min(state.chart.width-235,x+16));
    const top=Math.max(6,Math.min(state.chart.height-156,event.clientY-refs.wrap.getBoundingClientRect().top-34));
    refs.tooltip.style.left=left+"px";refs.tooltip.style.top=top+"px";refs.tooltip.hidden=false;
    render();
  }
  function chartEvents(){
    refs.wrap.addEventListener("pointerdown",e=>{
      if(e.button!==0||!state.bars.length)return;
      state.drag={x:posX(e),start:state.start,end:state.end,moved:false};
      refs.wrap.setPointerCapture(e.pointerId);
    });
    refs.wrap.addEventListener("pointermove",e=>{
      if(!state.bars.length)return;
      if(state.drag){
        const delta=posX(e)-state.drag.x;
        if(Math.abs(delta)>3)state.drag.moved=true;
        if(state.drag.moved){
          const span=state.drag.end-state.drag.start;
          const shift=Math.round(-delta/state.chart.plotWidth*(span-1));
          setRange(state.drag.start+shift,state.drag.end+shift,true);
          refs.tooltip.hidden=true;return;
        }
      }
      showTooltip(e);
    });
    refs.wrap.addEventListener("pointerup",e=>{state.drag=null;if(refs.wrap.hasPointerCapture(e.pointerId))refs.wrap.releasePointerCapture(e.pointerId);});
    refs.wrap.addEventListener("pointercancel",()=>state.drag=null);
    refs.wrap.addEventListener("pointerleave",()=>{if(!state.drag){refs.tooltip.hidden=true;state.hover=null;render();}});
    refs.wrap.addEventListener("wheel",e=>{
      if(!state.bars.length)return;
      e.preventDefault();
      const span=state.end-state.start;
      const newSpan=Math.max(12,Math.min(state.bars.length,Math.round(span*(e.deltaY<0?.78:1.28))));
      const ratio=Math.max(0,Math.min(1,(posX(e)-state.chart.left)/state.chart.plotWidth));
      const anchor=state.start+ratio*span;
      setRange(Math.round(anchor-ratio*newSpan),Math.round(anchor+(1-ratio)*newSpan),true);
      showTooltip(e);
    },{passive:false});
    refs.wrap.addEventListener("keydown",e=>{
      if(e.key==="ArrowLeft"||e.key==="ArrowRight"){
        e.preventDefault();const n=Math.max(1,Math.round((state.end-state.start)/10));
        const d=e.key==="ArrowLeft"?-n:n;setRange(state.start+d,state.end+d,true);
      }
    });
  }
  function downloadTrades(){
    if(!state.trades.length)return;
    const fields=["session","entry_uk","entry_price","target","stop","exit_uk","exit_price","exit_reason","gross_pts","gross_usd_1mes"];
    const rows=[fields.join(",")];
    for(const t of state.trades){
      rows.push([t.session,ukTime(state.bars[t.entryIndex].t),t.entry,t.target,t.stop,ukTime(state.bars[t.exitIndex].t),t.exit,t.reason,t.points,t.points*5].join(","));
    }
    const url=URL.createObjectURL(new Blob([rows.join("\n")+"\n"],{type:"text/csv;charset=utf-8;"}));
    const a=document.createElement("a");a.href=url;a.download="ASJR_MES_2026-10_VWAP_MeanReversion_Trades.csv";a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function main(){
    loadNames();renderStrategyList();chartEvents();
    refs.focus.add(new Option("Custom (zoom/pan)","custom"));
    $("add-strategy-form").addEventListener("submit",e=>{
      e.preventDefault();const input=$("new-strategy"),name=input.value.trim().replace(/\s+/g," ");
      if(!name||registry().some(s=>s.name.toLowerCase()===name.toLowerCase()))return;
      state.customStrategies.push(name);
      try{localStorage.setItem("asjr-chartlab-strategy-names-v1",JSON.stringify(state.customStrategies));}catch(_){}
      state.strategyId="draft-"+name.toLowerCase().replace(/[^a-z0-9]+/g,"-");
      input.value="";renderStrategyList();recalculate();
    });
    refs.focus.addEventListener("change",focusOnSelection);
    refs.session.addEventListener("change",()=>{if(refs.focus.value==="custom")refs.focus.value="session";focusOnSelection();});
    $("prev").addEventListener("click",()=>{refs.session.value=String(Math.max(0,Number(refs.session.value)-1));if(refs.focus.value==="custom")refs.focus.value="session";focusOnSelection();});
    $("next").addEventListener("click",()=>{refs.session.value=String(Math.min(state.sessions.length-1,Number(refs.session.value)+1));if(refs.focus.value==="custom")refs.focus.value="session";focusOnSelection();});
    $("reset").addEventListener("click",()=>{refs.focus.value="session";focusOnSelection();});
    ["show-vwap","show-ema9","show-ema20","show-trades","show-candles"].forEach(id=>$(id).addEventListener("change",render));
    $("recalculate").addEventListener("click",recalculate);
    $("export-trades").addEventListener("click",downloadTrades);
    new ResizeObserver(resize).observe(refs.wrap);
    try{
      const url=ROOT+DATASET.path;
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status+" loading MES CSV");
      const five=readCsv(await response.text());
      state.bars=makeBars(five);state.sessions=makeSessions(state.bars);
      if(!state.bars.length)throw Error("No completed 15-minute bars.");
      populateSessions();
      refs.status.textContent=five.length.toLocaleString("en-GB")+" × 5m · "+state.sessions.length+" sessions";
      refs.status.title="GitHub source downloaded successfully; October coverage audit remains NEEDS REVIEW.";
      focusOnSelection();recalculate();resize();
    }catch(error){
      refs.status.textContent="Data unavailable";refs.status.classList.add("error");
      refs.caption.textContent="Could not load October MES data: "+error.message;
      refs.tradeBody.replaceChildren(node("tr",null,"Historical source not loaded."));
    }
  }
  window.addEventListener("DOMContentLoaded",main);
})();
