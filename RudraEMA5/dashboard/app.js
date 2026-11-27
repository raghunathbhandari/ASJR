/* RudraEMA5 V2 · November 2026 interactive replay
 * Data is a frozen COHR IBKR 5m snapshot in data.js. No order routing.
 * For higher timeframes, only fully populated bars are aggregated from 5m.
 * The range restriction on C2 has been REMOVED per user request.
 */
(()=>{"use strict";
const DATA=window.RUDRAEMA5_RAW;
const $=id=>document.getElementById(id);
const FIRST=Date.UTC(2026,10,1), CUTOFF=Date.UTC(2026,10,27,18,0);
const DAYS=Array.from({length:27},(_,i)=>"2026-11-"+String(i+1).padStart(2,"0"));
const DAYS_LONG=new Intl.DateTimeFormat("en-GB",{weekday:"short",day:"2-digit",month:"short",timeZone:"UTC"});
const COLORS={bg:"#0c1420",grid:"#253449",tick:"#90a5bf",green:"#38c99a",red:"#f27889",amber:"#e9b95c",cyan:"#66d4e9",purple:"#aa9efa"};
let all=[],dayResults=[],barsByDay=new Map(),state={date:"2026-11-25",tf:5,rsi:36,swing:2,slope:.15};
let chartView={a:0,b:0,down:false,downX:0,origA:0,origB:0,hover:-1};
let chartGeom=null, lastDate="";
const fmt=(n,d=2)=>Number.isFinite(n)?Number(n).toFixed(d):"—";
const money=n=>Number.isFinite(n)?"$"+n.toFixed(2):"—";
const ret=n=>(n>0?"+":"")+fmt(n,2)+"R";
const klass=n=>n>0.000001?"pos":n<-.000001?"neg":"muted";
const when=t=>new Date(t).toISOString().slice(11,16);
const dateOf=t=>new Date(t).toISOString().slice(0,10);
const ceilCent=n=>Math.ceil((n-1e-9)*100)/100;
const number=(id,min,max,otherwise)=>{const v=+$(id).value;return Number.isFinite(v)?Math.min(max,Math.max(min,v)):otherwise};
function decode(){
 if(!Array.isArray(DATA)||!DATA.length)throw new Error("data.js is missing the November COHR candle dataset.");
 const out=DATA.map(a=>({ts:FIRST+a[0]*60000,o:a[1]/100,h:a[2]/100,l:a[3]/100,c:a[4]/100,v:a[5]}));
 if(out.some((r,i)=>r.ts>=CUTOFF||r.h<Math.max(r.o,r.c)||r.l>Math.min(r.o,r.c)||i&&r.ts<=out[i-1].ts))
 throw new Error("Source timestamp / OHLC validation failed.");
 return out;
}
function aggregate(raw,tf){
 if(tf===5)return raw.map(b=>({...b}));
 let groups=[], last=null;
 for(const b of raw){
  const bucket=Math.floor(b.ts/(tf*60000))*tf*60000;
  if(!last||last.start!==bucket){last={start:bucket,items:[]};groups.push(last)}
  last.items.push(b);
 }
 const expected=tf/5;
 return groups.filter(g=>g.items.length===expected&&g.items[0].ts===g.start&&g.items.every((x,i)=>i===0||x.ts-g.items[i-1].ts===300000)).map(g=>({
 ts:g.start,o:g.items[0].o,h:Math.max(...g.items.map(x=>x.h)),
 l:Math.min(...g.items.map(x=>x.l)),c:g.items.at(-1).c,
 v:g.items.reduce((z,x)=>z+x.v,0)
 }));
}
function indicators(arr){
 let ema=null,g=0,l=0;
 for(let i=0;i<arr.length;i++){
  const b=arr[i];ema=ema===null?b.c:(b.c+2*ema)/3;b.ema=ema;b.rsi=null;
  if(!i)continue;
  const change=b.c-arr[i-1].c,up=Math.max(0,change),down=Math.max(0,-change);
  if(i<=14){g+=up;l+=down;if(i!==14)continue;g/=14;l/=14}
  else{g=(g*13+up)/14;l=(l*13+down)/14}
  b.rsi=l===0?(g>0?100:50):100-100/(1+g/l);
 }
 return arr;
}
function evaluateDay(date,arr,settings){
 const thisDay=arr.filter(x=>dateOf(x.ts)===date);
 const trades=[], setups=[];let pos=null,c1Count=0,swingCount=0,rsiCount=0;
 function close(b,i,price,reason){
  const R=100*(price/pos.entry-1);
  trades.push({
   c1Index:pos.c1Index,entryIndex:pos.entryIndex,exitIndex:i,
   c1Time:pos.c1Time,entryTime:pos.entryTime,exitTime:b.ts,
   entry:pos.entry,exit:price,initialStop:pos.initialStop,reason,
   rsi:pos.rsi,swing:pos.swing,R,armed:pos.armed,stops:pos.stops
  });pos=null;
 }
 for(let i=25;i<arr.length;i++){
  const b=arr[i],day=dateOf(b.ts);
  if(day>date)break;if(day<date)continue;
  if(pos){
   if(b.o<=pos.activeStop){pos.stops.push({i,v:pos.activeStop});close(b,i,b.o,"Gap through stop");continue}
   if(b.l<=pos.activeStop){pos.stops.push({i,v:pos.activeStop});close(b,i,pos.activeStop,pos.armed?"Trailing stop":"Initial stop");continue}
   if(!pos.armed&&b.h>=pos.entry*1.01){pos.armed=true;pos.peak=b.h}
   if(pos.armed){
    pos.peak=Math.max(pos.peak,b.h);
    const newStop=Math.max(pos.activeStop,pos.peak*.998);
    pos.stops.push({i,v:newStop});
    if(b.c<=newStop){close(b,i,newStop,"Same-candle trailing exit");continue}
    pos.activeStop=newStop;
   }else pos.stops.push({i,v:pos.activeStop});
   continue;
  }
  const c1=arr[i-1],prev=arr[i-4],delta=settings.tf*60000;
  if(b.ts-c1.ts!==delta||c1.ts-prev.ts!==3*delta)continue;
  const slopePct=(c1.ema/prev.ema-1)*100;
  if(c1.h>=c1.ema||slopePct > -settings.slope)continue;
  c1Count++;
  const high=Math.max(...arr.slice(i-25,i-1).map(x=>x.h));
  const swing=100*(high-c1.l)/high;
  if(swing<settings.swing)continue;
  swingCount++;
  if(c1.rsi===null||c1.rsi>=settings.rsi)continue;
  rsiCount++;
  const trigger=Math.max(ceilCent(c1.h+.02),ceilCent(c1.c*1.002));
  setups.push({i:i-1,time:c1.ts,rsi:c1.rsi,swing,trigger,breakout:b.h>=trigger});
  if(b.h<trigger)continue;
  const entry=Math.max(b.o,trigger);
  pos={
   c1Index:i-1,entryIndex:i,c1Time:c1.ts,entryTime:b.ts,
   entry,initialStop:entry*.99,activeStop:entry*.99,
   armed:false,peak:entry,rsi:c1.rsi,swing,stops:[{i,v:entry*.99}]
  };
  if(b.l<=pos.activeStop){close(b,i,pos.activeStop,"Entry-bar stop (ambiguous)");continue}
  if(b.h>=entry*1.01){
   pos.armed=true;pos.peak=b.h;
   const newStop=Math.max(pos.activeStop,b.h*.998);
   pos.stops.push({i,v:newStop});
   if(b.c<=newStop){close(b,i,newStop,"Entry-bar trailing exit");continue}
   pos.activeStop=newStop;
  }
 }
 if(pos&&thisDay.length){
  const last=thisDay.at(-1),idx=arr.indexOf(last);
  pos.stops.push({i:idx,v:pos.activeStop});
  close(last,idx,last.c,"Day-end mark-to-market");
 }
 const wins=trades.filter(t=>t.R>0).length, losses=trades.filter(t=>t.R<0).length;
 return {date,candles:thisDay.length,c1Count,swingCount,rsiCount,setups,trades,wins,losses,
 sumR:trades.reduce((z,t)=>z+t.R,0),
 compPct:100*(trades.reduce((z,t)=>z*(1+t.R/100),1)-1),
 first:thisDay[0]?.ts||null,last:thisDay.at(-1)?.ts||null};
}
function getSettings(){
 const rsi=Number($("rsiLimit").value),swing=Number($("swing").value),slope=Number($("slope").value);
 return {date:$("date").value,tf:+$("tf").value,
 rsi:Number.isFinite(rsi)&&rsi>=5&&rsi<=95?rsi:36,
 swing:Number.isFinite(swing)&&swing>=0&&swing<=20?swing:2,
 slope:Number.isFinite(slope)&&slope>=0&&slope<=5?slope:.15};
}
function compute(){
 state=getSettings();
 all=indicators(aggregate(source,state.tf));
 barsByDay=new Map(DAYS.map(d=>[d,all.filter(x=>dateOf(x.ts)===d)]));
 dayResults=DAYS.map(d=>evaluateDay(d,all,state));
 $("rsiRule").textContent="<"+state.rsi;$("swingRule").textContent=fmt(state.swing)+"%";$("slopeRule").textContent=fmt(state.slope)+"%";
 if(state.tf===5&&state.rsi===36&&state.swing===2&&state.slope===.15){
  const count=dayResults.reduce((z,x)=>z+x.trades.length,0),sum=dayResults.reduce((z,x)=>z+x.sumR,0);
  if(count!==70||Math.abs(sum-(-4.5918471217))>.001)throw new Error("Baseline cross-check failed: the dashboard's 5m result does not match the committed November ledger.");
 }
 renderAll(true);
}
function totals(){
 const tr=dayResults.flatMap(x=>x.trades),wins=tr.filter(t=>t.R>0).length;
 return {trades:tr.length,wins,sumR:tr.reduce((z,t)=>z+t.R,0),profitDays:dayResults.filter(x=>x.sumR>0).length};
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
 $("chartTitle").textContent="COHR · "+state.tf+"m · "+state.date+" UK";
 $("dayInfo").textContent=day.candles?day.candles+" candles · "+day.c1Count+" base C1":"No data";
 renderTradeLog(day);renderTable();renderBars();
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
 '<div><dt>C1 setup</dt><dd>'+when(t.c1Time)+'</dd></div><div><dt>RSI at C1</dt><dd>'+fmt(t.rsi,2)+'</dd></div>'+
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
 const status=d.candles?d.candles<=12?" · Partial":"":" · No data";
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
 const dayStartIndex=all.findIndex(z=>dateOf(z.ts)===state.date);
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
for(const id of ["tf","rsiLimit","swing","slope"])$(id).addEventListener("change",()=>{try{compute()}catch(e){showError(e)}});
$("reset").addEventListener("click",()=>{$("tf").value="5";$("rsiLimit").value="36";$("swing").value="2";$("slope").value=".15";try{compute()}catch(e){showError(e)}});
$("export").addEventListener("click",()=>{
 const header=["date_uk","timeframe_min","candles","trades","wins","losses","win_rate_pct","gross_R","compounded_price_pct"];
 const values=dayResults.map(d=>[d.date,state.tf,d.candles,d.trades.length,d.wins,d.losses,d.trades.length?fmt(100*d.wins/d.trades,2):"",fmt(d.sumR,5),fmt(d.compPct,5)]);
 const csv=[header.join(","),...values.map(a=>a.join(","))].join("\n");
 const blob=new Blob([csv],{type:"text/csv;charset=utf-8"}),u=URL.createObjectURL(blob),a=document.createElement("a");
 a.href=u;a.download="RudraEMA5_COHR_Nov2026_"+state.tf+"min_daily.csv";a.click();URL.revokeObjectURL(u);
});
function showError(err){$("error").style.display="block";$("error").textContent="Dashboard error: "+String(err?.message||err)}
function init(){
 try{
  source=decode();
  $("date").innerHTML=DAYS.map(d=>'<option value="'+d+'">'+DAYS_LONG.format(new Date(d+"T12:00:00Z"))+" "+d.slice(0,4)+'</option>').join("");
  $("date").value=state.date;
  compute();new ResizeObserver(()=>draw()).observe(canvas);
 }catch(err){showError(err)}
}
let source=[];
init();
})();
