/* ASJR HotSector Lab | public GitHub CSV-driven viewer | research only */
"use strict";
(function(){
const BASE="https://raw.githubusercontent.com/raghunathbhandari/ASJR/main/";
const VIEW="https://github.com/raghunathbhandari/ASJR/blob/main/";
const MASTER="Rudra-HotSectorHotStock/november_2026_daily_top10_stocks.csv";
const LEADERS="Rudra-HotSectorHotStock/november_2026_sector_leaders.csv";
const SPY="three_candle/data/ibkr_bridge/research-1795712318577/SPY_2026-11-01_2026-11-25_15min_UTC.csv";
const SECTOR_LABELS={XLK:"Technology",XLY:"Consumer Discretionary",XLV:"Healthcare",XLE:"Energy",XLC:"Communication Services",XLP:"Consumer Staples",XLB:"Materials"};
const $=id=>document.getElementById(id);
const states={leaders:[],stocks:[],spy:{},selectedDate:"2026-11-02",selectedStock:"CVNA",stockFile:"",stockBars:[],requestId:0};
const fmt=x=>Number(x).toLocaleString("en-GB",{maximumFractionDigits:2});
const money=x=>"$"+Number(x).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=x=>!Number.isFinite(x)?"—":(x>=0?"+":"")+x.toFixed(2)+"%";
function parseCSV(text){
 const rows=[];let field="",arr=[],quoted=false;
 for(let i=0;i<text.length;i++){
  const ch=text[i];
  if(ch==='"'){
   if(quoted&&text[i+1]==='"'){field+='"';i++}else quoted=!quoted;
  }else if(ch===","&&!quoted){arr.push(field);field=""}
  else if((ch==="\n"||ch==="\r")&&!quoted){
   if(ch==="\r"&&text[i+1]==="\n")i++;
   arr.push(field);field="";
   if(arr.some(v=>v.trim()))rows.push(arr);
   arr=[];
  }else field+=ch;
 }
 if(field||arr.length){arr.push(field);rows.push(arr)}
 if(!rows.length)return[];
 const headers=rows.shift().map(x=>x.trim());
 return rows.map(row=>Object.fromEntries(headers.map((h,i)=>[h,(row[i]||"").trim()])));
}
async function getCSV(path){
 if(!path||!/^[A-Za-z0-9_./-]+\.csv$/.test(path)||path.includes(".."))throw Error("Unrecognised CSV source path");
 const response=await fetch(BASE+path+"?asjr="+Date.now(),{cache:"no-store"});
 if(!response.ok)throw Error("GitHub returned "+response.status+" for "+path);
 return parseCSV(await response.text());
}
function status(msg,error){
 $("status").textContent=msg;
 $("status").style.color=error?"var(--red)":"var(--muted)";
}
function option(value,title){
 const opt=document.createElement("option");opt.value=value;opt.textContent=title;return opt;
}
function setOptions(el,values,wanted){
 el.replaceChildren(...values.map(x=>option(x[0],x[1])));
 if(values.some(x=>x[0]===wanted))el.value=wanted;
 else if(values.length)el.value=values[0][0];
 return el.value;
}
function indexValue(day){return Object.hasOwn(states.spy,day)?states.spy[day]:NaN}
function datesFiltered(){
 const selectedSector=$("sector").value||"ALL",filter=$("indexFilter").value;
 return states.leaders.filter(row=>{
  if(selectedSector!=="ALL"&&row.leader_etf!==selectedSector)return false;
  const spy=indexValue(row.date_us),s=Number(row.leader_first_15m_pct);
  if(filter==="UP"&&!(spy>0))return false;
  if(filter==="DOWN"&&!(spy<0))return false;
  if(filter==="LEADER"&&!(Number.isFinite(spy)&&s>spy))return false;
  return true;
 });
}
function refreshDates(){
 const allowed=datesFiltered();
 states.selectedDate=setOptions($("session"),
  allowed.map(row=>[row.date_us,row.date_us+" · "+row.leader_etf]),
  states.selectedDate);
 refreshStocks();
}
function currentRows(){
 return states.stocks.filter(r=>r.date_us===states.selectedDate);
}
function refreshStocks(){
 const choices=currentRows();
 const selected=states.selectedStock;
 const selectedRow=states.leaders.find(r=>r.date_us===states.selectedDate);
 const statusText=selectedRow?selectedRow.top10_stock_status:"";
 const values=choices.length?choices.slice().sort((a,b)=>Number(a.rank)-Number(b.rank)).map(
  r=>[r.ticker,r.ticker+" · #"+r.rank+(r.ibkr_stock_5min_csv?" ✓":" · no candles")]
 ):[["","No ranked stocks yet"]];
 states.selectedStock=setOptions($("stock"),values,selected);
 $("listNote").textContent=choices.length
  ?"Rank is original web/day-end sample order; opening gains shown separately. "+choices.length+" stocks recorded."
  :"No stock shortlist for this date. "+statusText;
 renderList();
 updateMetrics();
 loadStock();
}
function setMetric(id,text,num){
 const el=$(id);el.textContent=text;
 el.classList.remove("pos","neg");
 if(Number.isFinite(num))el.classList.add(num>=0?"pos":"neg");
}
function updateMetrics(){
 const leader=states.leaders.find(r=>r.date_us===states.selectedDate);
 setMetric("sectorMetric",leader?(leader.leader_etf+" "+pct(Number(leader.leader_first_15m_pct))):"—");
 setMetric("spyMetric",pct(indexValue(states.selectedDate)),indexValue(states.selectedDate));
 const row=currentRows().find(r=>r.ticker===states.selectedStock);
 if(row){
  const gain=Number(row.ibkr_first_15min_gain_pct);
  setMetric("gainMetric",row.ibkr_first_15min_gain_pct?pct(gain):"Pending",row.ibkr_first_15min_gain_pct?gain:NaN);
  setMetric("volumeMetric",row.ibkr_first_15min_shares?fmt(row.ibkr_first_15min_shares):"Pending");
 }else{
  setMetric("gainMetric","—");setMetric("volumeMetric","—");
 }
}
function renderList(){
 const body=$("stocksBody");body.replaceChildren();
 const rows=currentRows();
 if(!rows.length){
  const tr=document.createElement("tr"),td=document.createElement("td");
  td.colSpan=6;td.textContent="No stock shortlist for this day. The sector ranking remains available.";
  tr.appendChild(td);body.appendChild(tr);return;
 }
 for(const row of rows.slice().sort((a,b)=>Number(a.rank)-Number(b.rank))){
  const tr=document.createElement("tr");if(states.selectedStock===row.ticker)tr.className="selected";
  const source=row.ibkr_stock_5min_csv?"Ready":"Pending";
  const values=[row.rank,row.ticker,row.ibkr_first_15min_gain_pct?pct(Number(row.ibkr_first_15min_gain_pct)):"—",
   row.ibkr_first_15min_shares?fmt(Number(row.ibkr_first_15min_shares)):"—",
   row.ibkr_max_upside_after_1445_pct?pct(Number(row.ibkr_max_upside_after_1445_pct)):"—",source];
  for(const val of values){const td=document.createElement("td");td.textContent=String(val);tr.appendChild(td)}
  tr.tabIndex=0;tr.setAttribute("role","button");
  tr.setAttribute("aria-label","View "+row.ticker+" 5-minute chart");
  const choose=()=>{$("stock").value=row.ticker;states.selectedStock=row.ticker;renderList();updateMetrics();loadStock()};
  tr.addEventListener("click",choose);
  tr.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose()}});
  body.appendChild(tr);
 }
}
async function loadStock(){
 const thisRequest=++states.requestId;
 states.stockBars=[];
 const selected=currentRows().find(r=>r.ticker===states.selectedStock);
 const link=$("stockSource");
 link.style.display="none";
 setMetric("entryMetric","—");
 if(!selected){
  $("plot").innerHTML='<div class="empty">No stock data researched for this date yet.<br>Choose another date or add IBKR data to the ASJR master CSV.</div>';
  $("chartTitle").textContent="Opening price action";
  return;
 }
 $("chartTitle").textContent=states.selectedStock+" · "+states.selectedDate+" · 5-minute candles";
 $("chartSub").textContent="14:30–14:45 UK selection window; entry model = 14:45 bar open.";
 if(!selected.ibkr_stock_5min_csv){
  $("plot").innerHTML='<div class="empty">IBKR 5-minute CSV not published for '+selected.ticker+' on '+selected.date_us+'.<br>It will appear here automatically after the master CSV is updated.</div>';
  $("tradeNote").textContent="Stock data pending. No entry or exit is simulated.";
  return;
 }
 $("plot").innerHTML='<div class="empty">Loading '+selected.ticker+' historical candles…</div>';
 try{
  const data=await getCSV(selected.ibkr_stock_5min_csv);
  if(thisRequest!==states.requestId)return;
  const bars=data.map(r=>{
   const datetime=r.Datetime_UTC||r.datetime_utc||"";
   const date=datetime.slice(0,10),tm=datetime.slice(11,16);
   return {date,time:tm,o:Number(r.Open),h:Number(r.High),l:Number(r.Low),c:Number(r.Close),v:Number(r.Volume)}
  }).filter(r=>r.date===states.selectedDate&&r.time>="14:30"&&r.time<"21:00"&&
   [r.o,r.h,r.l,r.c,r.v].every(Number.isFinite)).sort((a,b)=>a.time.localeCompare(b.time));
  if(!bars.length)throw Error("No US regular-session candles in published dataset");
  states.stockBars=bars;
  states.stockFile=selected.ibkr_stock_5min_csv;
  link.href=VIEW+states.stockFile;link.style.display="";
  $("sourceCaption").textContent=states.stockFile+" · UTC export · 14:30–21:00 UK in November.";
  draw();
 }catch(err){
  if(thisRequest!==states.requestId)return;
  $("plot").innerHTML='<div class="empty">Could not load stock candles. Check the published GitHub CSV path and browser network access.</div>';
  status("Chart data error: "+err.message,true);
 }
}
function elt(tag,attrs,text){
 const n=document.createElementNS("http://www.w3.org/2000/svg",tag);
 if(attrs)for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));
 if(text!==undefined)n.textContent=String(text);
 return n;
}
function renderLine(svg,x1,y1,x2,y2,color,width,dash,opacity){
 const attrs={x1,y1,x2,y2,stroke:color,"stroke-width":width||1};
 if(dash)attrs["stroke-dasharray"]=dash;
 if(opacity)attrs.opacity=opacity;
 svg.appendChild(elt("line",attrs));
}
function renderText(svg,x,y,text,color,size,anchor,weight){
 svg.appendChild(elt("text",{x,y,fill:color||"#9eafc1","font-size":size||12,
   "font-family":"system-ui,sans-serif","font-weight":weight||400,
   "text-anchor":anchor||"start"},text));
}
function draw(){
 const full=states.stockBars,number=Number($("window").value)||12;
 if(full.length<4){
  $("plot").innerHTML='<div class="empty">Too few regular-session bars to establish a completed first 15-minute signal and next-candle entry.</div>';
  return;
 }
 const bars=full.slice(0,number);
 const signal=full[2].c;
 const entry=full[3].o;
 const initialStop=entry*.99;
 const actualGain=(signal/full[0].o-1)*100;
 const volume=full.slice(0,3).reduce((a,r)=>a+r.v,0);
 setMetric("gainMetric",pct(actualGain),actualGain);
 setMetric("volumeMetric",fmt(volume));
 setMetric("entryMetric",money(entry)+" / "+money(initialStop));
 const firstExit=full.slice(3).find(r=>r.l<=initialStop);
 const exactStop=firstExit&&full.slice(3).indexOf(firstExit)===0;
 const result=simulate(full,entry);
 const note=result.reason==="STOP"?
   "Initial/stepped stop observed at "+result.time+" UK: estimated "+pct(result.gain)+
   " gross. This estimate excludes spread, fees, slippage and same-bar ordering.":result.reason==="AMBIGUOUS"?
   "High and low within the same five-minute candle cross a new trailing-stop milestone and its stop. Actual order is unknown; no precise exit gain is claimed.":
   "No confirmed stop hit under the conservative OHLC model before the available session end. Estimated close return "+pct(result.gain)+" gross, excluding costs.";
 $("tradeNote").textContent="Entry: "+money(entry)+" at 14:45 UK (next-bar open). Initial SL: "+money(initialStop)+
   ". "+note+(exactStop?" First post-entry candle tested the initial stop.":"");

 let lows=bars.map(r=>r.l),highs=bars.map(r=>r.h);
 lows.push(initialStop,entry);highs.push(initialStop,entry,signal);
 let low=Math.min(...lows),high=Math.max(...highs);
 const pad=(high-low)*.10||1;low-=pad;high+=pad;
 const W=1040,H=505,L=79,R=115,T=37,B=343,TOPVOL=375,BOTVOL=448;
 const plotW=W-L-R,step=plotW/bars.length;
 const x=i=>L+(i+.5)*step;
 const y=v=>B-(v-low)/(high-low)*(B-T);
 const maxVol=Math.max(...bars.map(r=>r.v))||1;
 const svg=elt("svg",{viewBox:"0 0 "+W+" "+H,role:"img","aria-label":states.selectedStock+" historical five-minute candlestick chart"});
 svg.appendChild(elt("rect",{x:L,y:T,width:step*3,height:BOTVOL-T+6,rx:5,fill:"#528bea","fill-opacity":".09"}));
 for(let i=0;i<5;i++){
  const price=low+(high-low)*i/4;
  renderLine(svg,L,y(price),W-R,y(price),"#607589",1,"4 6",.28);
  renderText(svg,W-R+12,y(price)+4,money(price),"#9aafbf",12);
 }
 renderText(svg,L+6,23,"FIRST 15 MIN — STOCK RANKING","#79abd9",13,"start",650);
 renderLine(svg,L+step*3,T,L+step*3,BOTVOL,"#79abd9",1.5,"5 5",.85);
 renderText(svg,L+step*3+7,56,"14:45 entry","#79abd9",12);
 renderLine(svg,L+step*3,y(entry),W-R,y(entry),"#79abd9",1.8,"7 5",.9);
 renderLine(svg,L+step*3,y(initialStop),W-R,y(initialStop),"#f07a86",1.8,"5 4",.9);
 renderText(svg,W-R+12,y(entry)-8,"Entry","#79abd9",12,"start",650);
 renderText(svg,W-R+12,y(initialStop)-8,"−1% SL","#f07a86",12,"start",650);
 renderText(svg,L+4,TOPVOL-12,"5-minute volume","#9eafc1",12);
 const stride=Math.max(1,Math.ceil(bars.length/12)),bodyWidth=Math.max(2,Math.min(step*.58,29));
 for(let i=0;i<bars.length;i++){
  const bar=bars[i],green=bar.c>=bar.o,color=green?"#36ba94":"#f07a86",px=x(i);
  renderLine(svg,px,y(bar.h),px,y(bar.l),color,1.8);
  const bodyTop=y(Math.max(bar.o,bar.c)),bodyBottom=y(Math.min(bar.o,bar.c));
  svg.appendChild(elt("rect",{x:px-bodyWidth/2,y:bodyTop,width:bodyWidth,
    height:Math.max(2,bodyBottom-bodyTop),fill:color,rx:1}));
  const vh=(bar.v/maxVol)*(BOTVOL-TOPVOL);
  svg.appendChild(elt("rect",{x:px-bodyWidth/2,y:BOTVOL-vh,width:bodyWidth,
   height:vh,fill:color,opacity:.57,rx:1}));
  if(i%stride===0||i===bars.length-1)renderText(svg,px,476,bar.time,"#a2b1c0",12,"middle");
  const hot=elt("rect",{x:px-step/2,y:T,width:step,height:BOTVOL-T,
   fill:"#fff",opacity:"0",style:"cursor:crosshair"});
  const show=()=>{
   $("candle-detail").textContent=states.selectedStock+" "+bar.time+" UK · Open "+money(bar.o)+
    " · High "+money(bar.h)+" · Low "+money(bar.l)+" · Close "+money(bar.c)+
    " · Volume "+fmt(bar.v);
  };
  hot.addEventListener("pointerenter",show);
  hot.addEventListener("pointermove",show);
  hot.addEventListener("click",show);
  hot.appendChild(elt("title",null,bar.time+" UK · O "+money(bar.o)+" H "+money(bar.h)+
     " L "+money(bar.l)+" C "+money(bar.c)+" · Vol "+fmt(bar.v)));
  svg.appendChild(hot);
 }
 const wrap=$("plot");wrap.replaceChildren(svg);
 if(firstExit&&number>=4){
  const idx=bars.indexOf(firstExit);
  if(idx>=0)renderText(svg,Math.min(W-R-130,x(idx)+13),
     Math.max(T+20,y(firstExit.l)-18),"Original SL touched","#f07a86",12);
 }
}
function simulate(bars,entry){
 let level=0,stop=entry*.99;
 for(const b of bars.slice(3)){
  if(b.o<stop)return {reason:"STOP",time:b.time,gain:100*(b.o/entry-1)};
  if(b.l<=stop)return {reason:"STOP",time:b.time,gain:100*(stop/entry-1)};
  const newLevel=Math.max(0,Math.floor((b.h/entry-1)*100+1e-8));
  if(newLevel>level){
   const newStop=entry*(1+(newLevel-1)*.01);
   if(b.l<=newStop)return {reason:"AMBIGUOUS",time:b.time,gain:NaN};
   level=newLevel;stop=newStop;
  }
 }
 return {reason:"EOD",time:"21:00",gain:100*(bars[bars.length-1].c/entry-1)};
}
async function loadCatalog(){
 const refreshToken=++states.requestId;
 status("Loading sector leaders, stock research CSV, and SPY benchmark from GitHub…",false);
 try{
  const [leaders,stocks,spyRows]=await Promise.all([getCSV(LEADERS),getCSV(MASTER),getCSV(SPY)]);
  if(refreshToken!==states.requestId)return;
  states.leaders=leaders.sort((a,b)=>a.date_us.localeCompare(b.date_us));
  states.stocks=stocks;
  states.spy={};
  for(const r of spyRows){
   if((r.Datetime_UTC||"").slice(11,16)==="14:30"){
    const day=r.Datetime_UTC.slice(0,10),o=Number(r.Open),c=Number(r.Close);
    if(o>0&&Number.isFinite(c))states.spy[day]=100*(c/o-1);
   }
  }
  const available=[...new Set(leaders.map(x=>x.leader_etf))].sort();
  setOptions($("sector"),[["ALL","All winning sectors"],...available.map(s=>[s,s+" · "+(SECTOR_LABELS[s]||s)])],$("sector").value||"ALL");
  refreshDates();
  status("GitHub research loaded · "+leaders.length+" sector sessions · "+
   stocks.length+" stock-day candidates · "+new Set(stocks.filter(r=>r.ibkr_stock_5min_csv).map(r=>r.date_us)).size+
   " dates with candle paths. Refresh to include new downloads.",false);
 }catch(e){
  status("Could not load GitHub research files: "+e.message,true);
  $("plot").innerHTML='<div class="empty">The dashboard needs access to the public ASJR CSV files. Confirm GitHub Pages is enabled and GitHub can load raw files.</div>';
 }
}
$("sector").addEventListener("change",refreshDates);
$("indexFilter").addEventListener("change",refreshDates);
$("session").addEventListener("change",()=>{
 states.selectedDate=$("session").value;states.selectedStock="";
 refreshStocks();
});
$("stock").addEventListener("change",()=>{
 states.selectedStock=$("stock").value;renderList();updateMetrics();loadStock();
});
$("window").addEventListener("change",draw);
$("refresh").addEventListener("click",loadCatalog);
loadCatalog();
})();