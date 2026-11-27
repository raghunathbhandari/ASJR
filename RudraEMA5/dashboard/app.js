/* RudraEMA5 V2/V3 multi-stock research dashboard; IBKR historical only. */
(()=>{"use strict";
const E=window.RudraEMA5Engine;
const OVERVIEW=window.RUDRAEMA5_OVERVIEW;
const $=id=>document.getElementById(id);
let DAYS=[],source=[],all=[],dayResults=[],barsByDay=new Map();
let state={symbol:"COHR",month:"2026-11",date:"2026-11-25",version:"V3",tf:5,rsi:36,swing:2,slope:.15};
const DAYS_LONG=new Intl.DateTimeFormat("en-GB",{weekday:"short",day:"2-digit",month:"short",timeZone:"Europe/London"});
const COLORS={bg:"#0c1420",grid:"#253449",tick:"#90a5bf",green:"#38c99a",red:"#f27889",amber:"#e9b95c",cyan:"#66d4e9",purple:"#aa9efa"};
let chartView={a:0,b:0,down:false,downX:0,origA:0,origB:0,hover:-1};
let chartGeom=null, lastDate="";
const fmt=(n,d=2)=>Number.isFinite(n)?Number(n).toFixed(d):"—";
const money=n=>Number.isFinite(n)?"$"+n.toFixed(2):"—";
const ret=n=>(n>0?"+":"")+fmt(n,2)+"R";
const klass=n=>n>0.000001?"pos":n<-.000001?"neg":"muted";
const when=t=>E.ukLabels(t).clock;
const dateOf=t=>E.ukLabels(t).day;
const ceilCent=n=>Math.ceil((n-1e-9)*100)/100;
const number=(id,min,max,otherwise)=>{const v=+$(id).value;return Number.isFinite(v)?Math.min(max,Math.max(min,v)):otherwise};
function makeDays(month){const [year,mon]=month.split("-").map(Number);const length=new Date(Date.UTC(year,mon,0)).getUTCDate();return Array.from({length},(_,i)=>month+"-"+String(i+1).padStart(2,"0"));}
function populateDates(requested){
 DAYS=makeDays(state.month);
 $("date").innerHTML=DAYS.map(d=>'<option value="'+d+'">'+DAYS_LONG.format(new Date(d+"T12:00:00Z"))+'</option>').join("");
 const fallback=state.month+"-"+(state.month==="2026-11"?"25":"15");
 let next=DAYS.includes(requested)?requested:fallback;
 $("date").value=next;state.date=next;
}
function getSettings(){
 const rsi=Number($("rsiLimit").value),swing=Number($("swing").value),slope=Number($("slope").value);
 return {symbol:$("symbol").value,month:$("month").value,version:$("version").value,
 date:$("date").value,tf:+$("tf").value,
 rsi:Number.isFinite(rsi)&&rsi>=5&&rsi<=95?rsi:36,
 swing:Number.isFinite(swing)&&swing>=0&&swing<=20?swing:2,
 slope:Number.isFinite(slope)&&slope>=0&&slope<=5?slope:.15};
}
async function ensureSymbol(symbol){
 if(window.RUDRAEMA5_ARCHIVE&&window.RUDRAEMA5_ARCHIVE[symbol])return;
 await new Promise((resolve,reject)=>{
  const s=document.createElement("script");s.src="./data/"+symbol+".js";s.async=true;
  s.onload=()=>window.RUDRAEMA5_ARCHIVE?.[symbol]?resolve():reject(new Error("Asset loaded but "+symbol+" candles missing"));
  s.onerror=()=>reject(new Error("Could not load historic candles for "+symbol));
  document.head.appendChild(s);
 });
}
function compute(){
 state=getSettings();
 if(!window.RUDRAEMA5_ARCHIVE?.[state.symbol])throw new Error("No archived 5-minute data for "+state.symbol);
 source=E.decode(window.RUDRAEMA5_ARCHIVE[state.symbol]);
 all=E.indicators(E.aggregate(source,state.tf));
 const result=E.replay(all,{timeframe:state.tf,version:state.version,rsi:state.rsi,swing:state.swing,slope:state.slope});
 const mapped=new Map(result.byDay.map(x=>[x.date,x]));
 const grouped=new Map();
 for(const b of all){if(!grouped.has(b.day))grouped.set(b.day,[]);grouped.get(b.day).push(b)}
 barsByDay=new Map(DAYS.map(day=>[day,grouped.get(day)||[]]));
 dayResults=DAYS.map(day=>mapped.get(day)||{date:day,candles:0,trades:[],setups:[],wins:0,losses:0,sumR:0,c1Count:0,swingCount:0,rsiCount:0});
 $("rsiRule").textContent="<"+state.rsi;$("swingRule").textContent=fmt(state.swing)+"%";$("slopeRule").textContent=fmt(state.slope)+"%";
 $("versionRule").textContent=state.version==="V3"?"RSI(C1) > RSI(previous completed candle)":"RSI rising requirement OFF (V2)";
 if(state.tf===5&&state.rsi===36&&state.swing===2&&state.slope===.15){
  const base=OVERVIEW?.stockMonths.find(x=>x.symbol===state.symbol&&x.month===state.month&&x.version===state.version);
  if(base){const n=dayResults.reduce((s,d)=>s+d.trades.length,0),sum=dayResults.reduce((s,d)=>s+d.sumR,0);
   if(n!==base.trades||Math.abs(sum-base.sumR)>.002)throw new Error("Replayed strategy does not match frozen 5m "+state.symbol+" "+state.month+" "+state.version+" research ledger");
  }
 }
 renderAll(true);
}
function totals(){
 const tr=dayResults.flatMap(x=>x.trades),wins=tr.filter(t=>t.R>0).length;
 return{trades:tr.length,wins,sumR:tr.reduce((s,t)=>s+t.R,0),profitDays:dayResults.filter(x=>x.sumR>0).length};
}
async function refreshSelector(changed){
 const selected=getSettings();
 if(changed==="symbol"&&selected.symbol==="COHR")$("month").value="2026-11";
 state={...selected,month:$("month").value};
 if(changed==="month"||changed==="symbol")populateDates(state.month+"-"+(selected.date||"2026-11-25").slice(-2));
 await ensureSymbol(state.symbol);
 compute();
}
function renderMatrix(){
 const el=$("matrixRows");if(!el||!OVERVIEW)return;
 const symbols=["AAPL","AMD","INTC","NVDA","PLTR","TSLA","COHR"];
 const rows=[];
 for(const s of symbols){for(const m of ["2026-09","2026-10","2026-11"]){
  if(s==="COHR"&&m!=="2026-11")continue;
  const a=OVERVIEW.stockMonths.find(x=>x.symbol===s&&x.month===m&&x.version==="V2");
  const b=OVERVIEW.stockMonths.find(x=>x.symbol===s&&x.month===m&&x.version==="V3");
  if(!a||!b)continue;
  const active=s===state.symbol&&m===state.month;
  rows.push('<tr tabindex="0" class="rowbtn'+(active?' selected':'')+'" data-sym="'+s+'" data-month="'+m+'" title="Open '+s+' '+m+'"><td>'+s+(s==="COHR"?' *':'')+'</td><td>'+m.slice(5)+'</td><td>'+a.trades+'</td><td class="'+klass(a.sumR)+'">'+ret(a.sumR)+'</td><td>'+b.trades+'</td><td>'+b.wins+'/'+b.trades+'</td><td class="'+klass(b.sumR)+'">'+ret(b.sumR)+'</td><td class="'+klass(b.sumR-a.sumR)+'">'+ret(b.sumR-a.sumR)+'</td></tr>');
 }}
 el.innerHTML=rows.join("");
 const v2=OVERVIEW.summary.V2,v3=OVERVIEW.summary.V3;
 $("matrixSub").textContent="Six-stock frozen 5m baseline (excludes COHR): V2 "+v2.trades+" trades / "+ret(v2.sumR)+" · V3 "+v3.trades+" trades / "+ret(v3.sumR);
}
function renderAll(resetZoom=false){
 const t=totals(),day=dayResults.find(x=>x.date===state.date),noData=!day.candles;
 $("kTrades").textContent=t.trades;
 $("kWins").textContent=t.trades?fmt(100*t.wins/t.trades,1)+"%":"—";
 $("kMonth").textContent=ret(t.sumR);$("kMonth").className="value "+klass(t.sumR);
 $("kDay").textContent=noData?"No data":ret(day.sumR);$("kDay").className="value "+(noData?"muted":klass(day.sumR));
 $("kDaySub").textContent=state.date+" · "+(day.candles?day.trades.length+" trades":"No available candles");
 $("kDayWins").textContent=noData?"—":day.wins+" / "+day.trades.length;
 $("kBars").textContent=day.candles+" candles · "+state.tf+"m bars";
 $("chartTitle").textContent=state.symbol+" · "+state.version+" · "+state.tf+"m · "+state.date+" UK";
 $("dayInfo").textContent=day.candles?day.candles+" candles · "+day.c1Count+" base C1":"No data";
 renderTradeLog(day);renderTable();renderBars();renderMatrix();
 if(resetZoom||lastDate!==state.date){
  const n=(barsByDay.get(state.date)||[]).length;
  chartView.a=0;chartView.b=Math.max(0,n-1);chartView.hover=-1;
 }
 lastDate=state.date;draw();
}
function selectDate(date){
 if(!DAYS.includes(date))return;state.date=date;$("date").value=date;
 renderAll(true);
}
function renderTradeLog(day){
 const el=$("tradelog");
 if(!day.candles){el.innerHTML='<div class="empty">No IBKR 5-minute bars for this UK date.<br>Calendar or market closure.</div>';return}
 if(!day.trades.length){el.innerHTML='<div class="empty">No triggered trades under the selected rules.<br><br>'+day.c1Count+' initial EMA/C1 candidates<br>'+day.swingCount+' meet swing rule<br>'+day.rsiCount+' meet RSI rule</div>';return}
 el.innerHTML='<h3>Price-based R · 1R = 1% of entry price</h3>'+
 day.trades.map((t,i)=>'<div class="trade"><div class="tradehead"><span>Trade '+(i+1)+'</span><span class="'+klass(t.R)+'">'+ret(t.R)+'</span></div><dl>'+
 '<div><dt>C1 setup</dt><dd>'+when(t.c1)+'</dd></div><div><dt>RSI at C1 / prior</dt><dd>'+fmt(t.rsi,2)+' / '+fmt(t.priorRsi,2)+'</dd></div>'+
 '<div><dt>BUY / entry</dt><dd>'+when(t.entryTime)+' · '+money(t.entry)+'</dd></div><div><dt>Initial stop</dt><dd>'+money(t.initialStop)+'</dd></div>'+
 '<div><dt>SELL / exit</dt><dd>'+when(t.exitTime)+' · '+money(t.exit)+'</dd></div><div><dt>Swing decline</dt><dd>'+fmt(t.swing,2)+'%</dd></div>'+
 '</dl><div class="sub" style="margin-top:11px">'+t.reason+'</div></div>').join("");
}
function renderTable(){
 const tbody=$("dayRows"),selected=state.date;
 tbody.innerHTML=dayResults.map(d=>{
 const w=d.trades.length?fmt(100*d.wins/d.trades,0)+"%":"—";
 const text=d.candles?ret(d.sumR):"—";
 const barWidth=Math.min(100,Math.abs(d.sumR)/5*100);
 const name=DAYS_LONG.format(new Date(d.date+"T12:00:00Z"));
 const status=d.candles&&d.candles<=Math.max(3,30/state.tf)?" · Partial":!d.candles?" · No data":"";
 return '<tr class="rowbtn'+(d.date===selected?' selected':'')+'" data-date="'+d.date+'" tabindex="0" title="Inspect '+d.date+'"><td>'+name+status+'</td><td>'+d.candles+'</td><td>'+d.trades.length+'</td><td>'+d.wins+'</td><td>'+w+'</td><td class="'+klass(d.sumR)+'">'+text+'</td><td class="barcell"><div class="bar '+(d.sumR<0?'down':'')+'" style="width:'+fmt(barWidth,2)+'%"></div></td></tr>';
 }).join("");
}
function renderBars(){
 const el=$("barsChart"),max=Math.max(.1,...dayResults.map(x=>Math.abs(x.sumR)));
 el.innerHTML=dayResults.map(d=>{
 const h=Math.min(99,Math.abs(d.sumR)/max*98),title=d.date+" · "+d.trades.length+" trades · "+ret(d.sumR);
 return '<div class="graphcol '+(d.date===state.date?'sel':'')+'" data-date="'+d.date+'" title="'+title+'"><div class="upslot"><div class="upbar" style="height:'+(d.sumR>0?h:0)+'%"></div></div><div class="downslot"><div class="downbar" style="height:'+(d.sumR<0?h:0)+'%"></div></div></div>';
 }).join("");
}
const canvas=$("chart"),ctx=canvas.getContext("2d");let pixels={};
function draw(){
 const rect=canvas.getBoundingClientRect(),w=Math.max(300,rect.width),h=Math.max(470,rect.height),scale=Math.min(window.devicePixelRatio||1,2);
 if(!ctx)return;
 canvas.width=Math.round(w*scale);canvas.height=Math.round(h*scale);ctx.setTransform(scale,0,0,scale,0,0);
 ctx.clearRect(0,0,w,h);ctx.fillStyle="#0d1724";ctx.fillRect(0,0,w,h);
 const selected=dayResults.find(x=>x.date===state.date),db=barsByDay.get(state.date)||[];
 const left=15,right=w-69,top=20,bottom=h-160,rsiTop=h-119,rsiBottom=h-45;
 if(!db.length){ctx.fillStyle="#91a3bc";ctx.font="14px system-ui";ctx.textAlign="center";ctx.fillText("No candles for "+state.date,w/2,h/2);return}
 const a=Math.max(0,Math.min(chartView.a,db.length-1)),b=Math.max(a,Math.min(chartView.b,db.length-1)),span=b-a+1;
 const vis=db.slice(a,b+1),step=(right-left)/span,x=j=>left+(j-a+.5)*step;
 let priceMin=Math.min(...vis.map(v=>Math.min(v.l,v.ema))),priceMax=Math.max(...vis.map(v=>Math.max(v.h,v.ema)));
 const pad=Math.max(.4,(priceMax-priceMin)*.1);priceMin-=pad;priceMax+=pad;
 const y=p=>top+(priceMax-p)/(priceMax-priceMin)*(bottom-top);
 const ry=v=>rsiTop+(100-v)/100*(rsiBottom-rsiTop);
 chartGeom={w,h,left,right,top,bottom,rsiTop,rsiBottom,step,a,b,x,y,ry};
 ctx.font="11px system-ui";ctx.textBaseline="middle";
 for(let k=0;k<=5;k++){
  const v=priceMin+(priceMax-priceMin)*k/5,yy=y(v);
  ctx.strokeStyle="#273548";ctx.lineWidth=.75;ctx.setLineDash([]);
  ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();
  ctx.fillStyle="#a7b6c8";ctx.textAlign="left";ctx.fillText("$"+fmt(v,2),right+6,yy);
 }
 const stride=Math.max(1,Math.ceil(span/9));
 for(let j=Math.ceil(a/stride)*stride;j<=b;j+=stride){
  const xx=x(j);ctx.strokeStyle="#1c2939";ctx.beginPath();ctx.moveTo(xx,top);ctx.lineTo(xx,bottom);ctx.stroke();
  ctx.fillStyle="#8396ae";ctx.textAlign="center";ctx.fillText(when(db[j].ts),xx,bottom+21);
 }
 // Price EMA5 and OHLC candlesticks.
 ctx.save();ctx.strokeStyle=COLORS.amber;ctx.lineWidth=2.2;ctx.lineJoin="round";ctx.beginPath();
 for(let j=a;j<=b;j++){if(j===a)ctx.moveTo(x(j),y(db[j].ema));else ctx.lineTo(x(j),y(db[j].ema))}
 ctx.stroke();ctx.restore();
 for(let j=a;j<=b;j++){
  const d=db[j],xx=x(j),color=d.c>=d.o?COLORS.green:COLORS.red;
  ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(xx,y(d.h));ctx.lineTo(xx,y(d.l));ctx.stroke();
  const bw=Math.max(1.2,Math.min(12,step*.65));
  ctx.fillRect(xx-bw/2,Math.min(y(d.o),y(d.c)),bw,Math.max(1.3,Math.abs(y(d.o)-y(d.c))));
 }
 // RSI pane with 30, 36 and 70 reference levels.
 ctx.fillStyle="#101c2b";ctx.fillRect(left,rsiTop,right-left,rsiBottom-rsiTop);
 for(const [level,col] of [[30,"#a85c6e"],[36,"#a8a0e9"],[70,"#6c7b94"]]){
  const yy=ry(level);ctx.strokeStyle=col;ctx.globalAlpha=.7;ctx.lineWidth=1;ctx.setLineDash([4,4]);
  ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;
  ctx.textAlign="left";ctx.fillStyle=col;ctx.fillText(String(level),right+7,yy);
 }
 ctx.strokeStyle=COLORS.purple;ctx.lineWidth=1.8;ctx.beginPath();let started=false;
 for(let j=a;j<=b;j++){if(db[j].rsi==null)continue;if(!started){ctx.moveTo(x(j),ry(db[j].rsi));started=true}else ctx.lineTo(x(j),ry(db[j].rsi))}
 if(started)ctx.stroke();
 ctx.font="bold 10px system-ui";ctx.fillStyle="#9eacc2";ctx.fillText("RSI 14",left+7,rsiTop+13);
 // Entry/exit overlays use index in global array, translated to local day index.
 const dayStartIndex=all.findIndex(z=>z.day===state.date);
 const rel=i=>i-dayStartIndex;
 for(const s of selected.setups){
  const ix=rel(s.i);if(ix<a||ix>b)continue;
  const xx=x(ix),yy=y(db[ix].l)+11;ctx.fillStyle=COLORS.cyan;
  ctx.beginPath();ctx.moveTo(xx,yy-5);ctx.lineTo(xx+5,yy);ctx.lineTo(xx,yy+5);ctx.lineTo(xx-5,yy);ctx.closePath();ctx.fill();
 }
 for(const t of selected.trades){
  const ei=rel(t.entryIndex),xi=rel(t.exitIndex);if(ei>b||xi<a)continue;
  if(ei<=b&&xi>=a){
   const x1=x(Math.max(a,ei)),x2=x(Math.min(b,xi));
   ctx.fillStyle=t.R>=0?"#3bc79b09":"#f2788909";ctx.fillRect(x1,top,Math.max(1,x2-x1),bottom-top);
   ctx.strokeStyle="#43ca9d99";ctx.setLineDash([5,3]);ctx.lineWidth=1;
   ctx.beginPath();ctx.moveTo(x1,y(t.entry));ctx.lineTo(x2,y(t.entry));ctx.stroke();
   ctx.strokeStyle="#dc728daa";ctx.beginPath();ctx.moveTo(x1,y(t.initialStop));ctx.lineTo(x2,y(t.initialStop));ctx.stroke();ctx.setLineDash([]);
   if(t.stops.length>1){
    ctx.strokeStyle="#9d83f5";ctx.lineWidth=1.5;ctx.beginPath();let first=true;
    for(const pt of t.stops){const z=rel(pt.i);if(z<a||z>b)continue;
      if(first){ctx.moveTo(x(z),y(pt.v));first=false}else ctx.lineTo(x(z),y(pt.v))}
    if(!first)ctx.stroke();
   }
  }
  if(ei>=a&&ei<=b)marker(x(ei),y(t.entry),COLORS.green,true,"B");
  if(xi>=a&&xi<=b)marker(x(xi),y(t.exit),COLORS.red,false,"X");
 }
 if(chartView.hover>=a&&chartView.hover<=b){
  const j=chartView.hover,xx=x(j),yy=y(db[j].c);
  ctx.strokeStyle="#92a6c1";ctx.lineWidth=1;ctx.setLineDash([3,4]);
  ctx.beginPath();ctx.moveTo(xx,top);ctx.lineTo(xx,rsiBottom);ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.setLineDash([]);
 }
 ctx.fillStyle="#9bacc4";ctx.textAlign="left";ctx.font="10px system-ui";
 ctx.fillText("Price (USD)",left+4,top+7);
}
function marker(x,y,color,buy,label){
 ctx.save();ctx.fillStyle=color;ctx.strokeStyle="#0d1724";ctx.lineWidth=1.7;ctx.beginPath();
 if(buy){ctx.moveTo(x,y-9);ctx.lineTo(x-7,y+5);ctx.lineTo(x+7,y+5);ctx.closePath()}
 else ctx.arc(x,y,6,0,Math.PI*2);
 ctx.fill();ctx.stroke();ctx.font="bold 10px system-ui";ctx.fillStyle=color;
 ctx.textAlign="center";ctx.fillText(label,x,y+(buy?-19:19));ctx.restore();
}
function onMove(e){
 if(!chartGeom)return;
 const r=canvas.getBoundingClientRect(),xx=e.clientX-r.left;
 if(chartView.down){
  const shifted=Math.round((e.clientX-chartView.downX)/chartGeom.step);
  const count=chartView.origB-chartView.origA+1,db=barsByDay.get(state.date)||[];
  const start=Math.max(0,Math.min(db.length-count,chartView.origA-shifted));
  chartView.a=start;chartView.b=start+count-1;draw();return;
 }
 const db=barsByDay.get(state.date)||[];
 if(xx<chartGeom.left||xx>chartGeom.right){$("tooltip").style.display="none";return}
 const j=Math.max(chartGeom.a,Math.min(chartGeom.b,chartGeom.a+Math.floor((xx-chartGeom.left)/chartGeom.step)));
 chartView.hover=j;const b=db[j];if(!b)return;
 const tt=$("tooltip");tt.style.display="block";
 tt.innerHTML='<b>'+when(b.ts)+' UK</b> &nbsp;<span style="color:#e9b95c">EMA5 '+money(b.ema)+'</span><br>'+
 'O '+money(b.o)+' · H '+money(b.h)+'<br>L '+money(b.l)+' · C '+money(b.c)+'<br>RSI14 '+(b.rsi==null?"—":fmt(b.rsi,2))+' · Volume '+Math.round(b.v).toLocaleString("en-GB");
 tt.style.left=Math.min(Math.max(8,xx+16),Math.max(8,r.width-tt.offsetWidth-8))+"px";draw();
}
canvas.addEventListener("wheel",e=>{
 e.preventDefault();const d=barsByDay.get(state.date)||[];if(d.length<=8||!chartGeom)return;
 const oldCount=chartView.b-chartView.a+1;
 const count=Math.max(9,Math.min(d.length,Math.round(oldCount*(e.deltaY<0?.82:1.22))));
 const pos=Math.max(0,Math.min(1,((e.clientX-canvas.getBoundingClientRect().left)-chartGeom.left)/(chartGeom.right-chartGeom.left)));
 let a=Math.round(chartView.a+oldCount*pos-count*pos);a=Math.max(0,Math.min(d.length-count,a));
 chartView.a=a;chartView.b=a+count-1;draw();
},{passive:false});
canvas.addEventListener("pointerdown",e=>{if(e.button!==0||!chartGeom)return;chartView.down=true;chartView.downX=e.clientX;chartView.origA=chartView.a;chartView.origB=chartView.b;canvas.setPointerCapture?.(e.pointerId)});
canvas.addEventListener("pointerup",()=>chartView.down=false);
canvas.addEventListener("pointercancel",()=>chartView.down=false);
canvas.addEventListener("pointermove",onMove);
canvas.addEventListener("pointerleave",()=>{if(chartView.down)return;chartView.hover=-1;$("tooltip").style.display="none";draw()});
$("dayRows").addEventListener("click",e=>{const target=e.target.closest("[data-date]");if(target)selectDate(target.dataset.date)});
$("dayRows").addEventListener("keydown",e=>{if(e.key!=="Enter"&&e.key!==" ")return;const t=e.target.closest("[data-date]");if(t){e.preventDefault();selectDate(t.dataset.date)}});
$("barsChart").addEventListener("click",e=>{const t=e.target.closest("[data-date]");if(t)selectDate(t.dataset.date)});
$("date").addEventListener("change",e=>selectDate(e.target.value));
$("symbol").addEventListener("change",()=>refreshSelector("symbol").catch(showError));
$("month").addEventListener("change",()=>refreshSelector("month").catch(showError));
$("version").addEventListener("change",()=>refreshSelector("version").catch(showError));
for(const id of ["tf","rsiLimit","swing","slope"])$(id).addEventListener("change",()=>{try{compute()}catch(e){showError(e)}});
$("matrixRows").addEventListener("click",e=>{const el=e.target.closest("[data-sym]");if(!el)return;$("symbol").value=el.dataset.sym;$("month").value=el.dataset.month;$("version").value="V3";refreshSelector("symbol").catch(showError)});
$("matrixRows").addEventListener("keydown",e=>{if(e.key!=="Enter"&&e.key!==" ")return;const el=e.target.closest("[data-sym]");if(!el)return;e.preventDefault();$("symbol").value=el.dataset.sym;$("month").value=el.dataset.month;$("version").value="V3";refreshSelector("symbol").catch(showError)});
$("reset").addEventListener("click",()=>{$("version").value="V3";$("tf").value="5";$("rsiLimit").value="36";$("swing").value="2";$("slope").value=".15";try{compute()}catch(e){showError(e)}});
$("export").addEventListener("click",()=>{
 const header=["symbol","uk_date","version","timeframe_min","candles","trades","wins","losses","win_rate_pct","gross_R","compounded_price_pct"];
 const values=dayResults.map(d=>{const compound=100*(d.trades.reduce((acc,t)=>acc*(1+t.R/100),1)-1);
 return[state.symbol,d.date,state.version,state.tf,d.candles,d.trades.length,d.wins,d.losses,d.trades.length?fmt(100*d.wins/d.trades,2):"",fmt(d.sumR,5),fmt(compound,5)]});
 const csv=[header.join(","),...values.map(a=>a.join(","))].join("\n");
 const blob=new Blob([csv],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");
 a.href=url;a.download="RudraEMA5_"+state.symbol+"_"+state.month+"_"+state.version+"_"+state.tf+"m.csv";a.click();URL.revokeObjectURL(url);
});
function showError(err){$("error").style.display="block";$("error").textContent="Dashboard error: "+String(err?.message||err)}
async function init(){
 try{
  $("symbol").value=state.symbol;$("month").value=state.month;$("version").value=state.version;
  populateDates(state.date);
  await ensureSymbol(state.symbol);
  compute();
  if(typeof ResizeObserver!=="undefined")new ResizeObserver(()=>draw()).observe(canvas);
  else window.addEventListener("resize",()=>draw());
 }catch(err){showError(err)}
}
init();
})();
