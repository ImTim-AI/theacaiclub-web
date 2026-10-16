import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import * as points from '../src/lib/points.js';
const uuid='00000000-0000-4000-8000-000000000001';
const levels=[{label:'Fixture reward',cost:123,departmentIds:[21],productIds:[],excludeName:'mini'}];
const line={pid:511,departmentId:21,n:'Fixture drink',q:2,pointsUnits:1,pointsLabel:'Fixture reward',pointsEach:123};
const status={live:true,balance:500,available:246,rewards:[{kind:'category',id:uuid,name:'Fixture reward',pointsCost:123,repeatable:true,eligibility:{departmentIds:[21]}}]};
const request=points.bindRewards(points.selection([line],levels),status);
const quote={locationId:3,catalogueId:1,total:8.4,subtotal:8.4,lines:[{productId:511,name:'Fixture drink',departmentId:21,quantity:2,basePrice:3.2,unitPrice:4.2,subtotal:8.4,saleTaxId:0,modifiers:[{id:42,name:'Extra',price:1}]}]};
export const example=points.paymentBody({quote,request,userId:42,email:'fixture@example.test',notes:'Takeaway',deliveryTime:'2026-10-12T12:00:00.000Z',id:'fixture-order'});
const response=()=>({orderToken:'fixture-token',clientSecret:'fixture-secret',points:{reserved:true,pointsReserved:123,items:[{lineIndex:0,rewardId:uuid,units:1,pointsCost:123,discountPence:320}]}});

test('configuration only: arbitrary costs, product OR department, exclusions and ambiguity',()=>{
 assert.equal(points.levelFor(line,levels).cost,123);
 assert.equal(points.levelFor({...line,n:'Mini drink'},levels),null);
 assert.equal(points.levelFor(line,[...levels,...levels]),null);
 assert.equal(points.levelFor({...line,departmentId:null},[{...levels[0],productIds:[511]}]).cost,123);
 assert.deepEqual(points.parseLevels(null),[]);
 assert.deepEqual(points.parseLevels([{...levels[0],cost:'123'}]),[]);
 assert.deepEqual(points.parseLevels([{...levels[0],departmentIds:['21']}]),[]);
});
test('department 0 never matches a department level (server covers() rule)',()=>{
 assert.equal(points.levelFor({...line,departmentId:0},[{...levels[0],departmentIds:[0,21]}]),null);
});
test('excludeName is checked against the server product name as well as the menu name',()=>{
 assert.equal(points.levelFor({...line,serverName:'Mini Fixture drink'},levels),null);
});

// Backend #81: rewards_config.pointsRewards[].excludeProductIds, passed through
// points_catalogue as eligibility.excludeProductIds. Exclusion wins over inclusion.
test('#81: a config exclusion is never offered, by department or by product id',()=>{
 const byDept=[{...levels[0],excludeProductIds:[511]}];
 assert.equal(points.levelFor(line,byDept),null);
 assert.equal(points.levelFor({...line,pid:512},byDept).cost,123);
 assert.equal(points.levelFor(line,[{...levels[0],departmentIds:[],productIds:[511],excludeProductIds:[511]}]),null);
 assert.equal(points.levelFor(line,[{...levels[0],excludeProductIds:[]}]).cost,123);
 assert.deepEqual(points.parseLevels([{...levels[0],excludeProductIds:['511']}]),[]);
 assert.deepEqual(points.parseLevels([{...levels[0],excludeProductIds:511}]),[]);
});
test('#81: an excluded product on one level does not make another level ambiguous',()=>{
 const two=[{label:'Mini',cost:600,productIds:[437],departmentIds:[]},{label:'Bowl',cost:900,productIds:[],departmentIds:[20],excludeProductIds:[437]}];
 assert.equal(points.levelFor({pid:437,departmentId:20,n:'Bowl 437',q:1},two).label,'Mini');
 assert.equal(points.levelFor({pid:438,departmentId:20,n:'Bowl 438',q:1},two).label,'Bowl');
});
test('#81: binding honours the server catalogue exclusion, and works when the server has none (pre-#81)',()=>{
 const sel=points.selection([line],levels);
 const post81={...status,rewards:[{...status.rewards[0],eligibility:{departmentIds:[21],excludeProductIds:[511]}}]};
 assert.throws(()=>points.bindRewards(sel,post81),{message:points.notConfirmed});
 assert.deepEqual(points.bindRewards(sel,status),request);
 assert.equal(points.parseStatus({...status,rewards:[{...status.rewards[0],eligibility:{departmentIds:[21],excludeProductIds:['511']}}]}),null);
 assert.ok(points.parseStatus(post81));
});
test('status fails closed; negative balances are preserved',()=>{
 assert.equal(points.parseStatus({live:false}),null);
 assert.equal(points.parseStatus({...status,balance:'500'}),null);
 assert.equal(points.parseStatus({...status,rewards:[...status.rewards,...status.rewards]}),null);
 assert.equal(points.parseStatus({...status,balance:-50,available:-100}).balance,-50);
});
test('app wire request binds exact config label, cost, eligibility and availability to UUID',()=>{
 assert.deepEqual(request,{rewards:[{lineIndex:0,productId:511,rewardId:uuid,units:1,pointsEach:123}],totalPoints:123});
 for(const bad of [null,{...status,available:122},{...status,rewards:[]},{...status,rewards:[...status.rewards,...status.rewards]}, {...status,rewards:[{...status.rewards[0],pointsCost:124}]}, {...status,rewards:[{...status.rewards[0],eligibility:{}}]}])assert.throws(()=>points.bindRewards(points.selection([line],levels),bad));
 assert.throws(()=>points.selection([{...line,q:0}],levels));
 assert.throws(()=>points.selection([line],[{...levels[0],cost:124}]));
 assert.throws(()=>points.bindRewards(points.selection([{...line,pointsUnits:2}],levels),{...status,rewards:[{...status.rewards[0],repeatable:false}]}));
});
test('paid extras remain charged and exact app top-level shape is used',()=>{
 assert.equal(example.body.amount,520);
 assert.equal(example.body.order.items[0].discountAmount,3.2);
 assert.equal(example.body.order.items[0].netAmount,5.2);
 assert.deepEqual(Object.keys(example.body),['order','amount','currency','userId','clientCapabilities','points']);
 assert.deepEqual(example.body.clientCapabilities,['points_v1']);
 assert.deepEqual(example.discounts,{0:320});
 assert.equal(example.body.order.items[0].options[0].price,1);
 assert.equal(example.body.order.storeType,'Website');
});
test('saleTaxId is normalised like order-pay (missing -> 0)',()=>{
 const q={...quote,lines:[{...quote.lines[0],saleTaxId:null}]};
 assert.equal(points.paymentBody({quote:q,request,userId:42,email:'e',notes:'n',deliveryTime:'t',id:'i'}).body.order.items[0].saleTaxId,0);
});
test('a card remainder Stripe would refuse (1p-29p) is stopped before any hold is taken',()=>{
 const q=c=>({...quote,total:3.2+c/100,lines:[{...quote.lines[0],quantity:1,unitPrice:3.2+c/100,subtotal:3.2+c/100}]});
 const one=points.bindRewards(points.selection([{...line,q:1}],levels),status);
 for(const c of [1,29])assert.throws(()=>points.paymentBody({quote:q(c),request:one,userId:42,email:'e',notes:'n',deliveryTime:'t',id:'i'}),{message:points.belowCardMinimum});
 for(const c of [0,30])assert.equal(points.paymentBody({quote:q(c),request:one,userId:42,email:'e',notes:'n',deliveryTime:'t',id:'i'}).body.amount,c);
});
test('reservation must confirm every field and exact discount, with no duplicate lines',()=>{
 assert.equal(points.reservationConfirmed(request,response(),example.discounts),true);
 for(const r of [{}, {points:{}}, {...response(),points:{...response().points,reserved:1}}, {...response(),points:{...response().points,pointsReserved:124}}])assert.equal(points.reservationConfirmed(request,r,example.discounts),false);
 for(const [key,value] of Object.entries({lineIndex:1,rewardId:'wrong',units:2,pointsCost:124,discountPence:321})){
  const r=response();r.points.items[0][key]=value;assert.equal(points.reservationConfirmed(request,r,example.discounts),false,key);
 }
 const r=response();r.points.items.push({...r.points.items[0]});assert.equal(points.reservationConfirmed(request,r,example.discounts),false);
});
test('card earning rounds once on actual paid pence',()=>{
 assert.equal(points.earnedPoints(9.95),100);assert.equal(points.earnedPoints(19.9),199);assert.equal(points.earnedPoints(0),0);assert.equal(points.earnedPoints(5.2),52);
});

// order-pay's own conversion (supabase/functions/order-pay/index.ts ukOffsetMinutes /
// ukWallIsoToInstant at backend c8bbb96), copied verbatim as the oracle.
function orderPayUkOffsetMinutes(atMs){
 const wall=new Date(new Date(atMs).toLocaleString('en-US',{timeZone:'Europe/London'}));
 const utc=new Date(new Date(atMs).toLocaleString('en-US',{timeZone:'UTC'}));
 return Math.round((wall.getTime()-utc.getTime())/60000);
}
function orderPayWallToInstant(wallIso){
 const t=new Date(wallIso);if(isNaN(t.getTime()))return null;
 let instant=t.getTime()-orderPayUkOffsetMinutes(t.getTime())*60000;
 instant=t.getTime()-orderPayUkOffsetMinutes(instant)*60000;return new Date(instant);
}
test('scheduled pickup: delivery_time is the same instant order-pay would save (BST and GMT)',()=>{
 assert.equal(points.deliveryTimeFor({slotIso:'2026-10-16T17:30:00.000Z'}),'2026-10-16T16:30:00.000Z'); // BST
 assert.equal(points.deliveryTimeFor({slotIso:'2026-11-16T17:30:00.000Z'}),'2026-11-16T17:30:00.000Z'); // GMT
 // every 15 minutes across both 2026 clock changes
 for(const start of [Date.UTC(2026,2,28,12),Date.UTC(2026,9,24,12)])for(let t=start;t<start+36*3600000;t+=15*60000){
  const iso=new Date(t).toISOString();
  assert.equal(points.deliveryTimeFor({slotIso:iso}),orderPayWallToInstant(iso).toISOString(),iso);
 }
 assert.equal(points.deliveryTimeFor({mode:'in_store'},0),new Date(5*60000).toISOString());
 assert.equal(points.deliveryTimeFor({mode:'takeaway'},0),new Date(15*60000).toISOString());
 assert.throws(()=>points.deliveryTimeFor({slotIso:'nonsense'}));
});

// Execute the real page handlers with a fake DOM and network; no production calls.
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const pageSource=src=>src.split('<script>')[1].split('</script>')[0].replace(/^import .*;$/m,'');
const source=pageSource(readFileSync(new URL('../src/pages/order/index.astro',import.meta.url),'utf8'));
function harness({src=source,guest=false,selected=true,reply=response(),defer=false,free=false,slot=null,pts=status,lv=levels,q=null}={}){
 const elements=new Map();
 const el=id=>{if(!elements.has(id))elements.set(id,{style:{},classList:{add(){},remove(){},toggle(){},contains(){return false}},dataset:{},value:'',checked:true,textContent:'',innerHTML:'',addEventListener(){},querySelectorAll(){return []},scrollIntoView(){},setAttribute(){},removeAttribute(){},focus(){}});return elements.get(id);};
 const calls=[],listeners={};let mounted=0,charged=0,pending;
 const context=vm.createContext({...points,console,Date,Math,JSON,Promise,Intl,Object,Number,crypto:{randomUUID:()=> 'test-id'},setTimeout:()=>1,clearTimeout(){},
  document:{getElementById:el,querySelector:()=>el('footer'),querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(t,f){(listeners[t]=listeners[t]||[]).push(f);},scrollTo(){}},localStorage:{setItem(){},getItem(){return null},removeItem(){}},location:{origin:'http://local.test'},
  Stripe:()=>({elements:()=>{mounted++;return {create:()=>({mount(){}})}},confirmPayment:async()=>{charged++;return {}}}),
  fetch:async(url,opts)=>{const body=JSON.parse(opts.body||'{}');calls.push({fn:url.split('/').pop(),url,method:opts.method,headers:opts.headers,keepalive:opts.keepalive,rawBody:opts.body,body});let data;
   if(url.endsWith('/link-profile'))data={poscraftCustomerId:42};
   else if(url.endsWith('/points'))data=body.action==='release'?{released:true}:pts;
   else if(url.endsWith('/create-payment-intent')){if(defer)data=await new Promise(resolve=>pending=resolve);else data=reply;}
   else if(url.endsWith('/order-pay'))data={clientSecret:'guest-secret'};
   else if(url.endsWith('/process-order'))data={success:true};
   else throw Error('Unexpected mocked endpoint '+url);
   return {ok:true,json:async()=>data};
  }});
 const setup=`
  store={id:3,name:'Test store'};sched[3]={isAcceptingOrders:true};
  cart=${JSON.stringify([{...line,q:free?1:2,pointsUnits:selected?1:0,unit:free?3.2:4.2,extras:['Extra'],modIds:[42]}])};
  levels=${JSON.stringify(lv)};lastQuote=${JSON.stringify(q||(free?{...quote,total:3.2,subtotal:3.2,lines:[{...quote.lines[0],quantity:1,unitPrice:3.2,subtotal:3.2,modifiers:[]}]}:quote))};pointsStatus=${JSON.stringify(pts)};
  sess=${guest?'null':JSON.stringify({access_token:'fixture-jwt',expires_at:4102444800,email:'fixture@example.test'})};
  ${slot?`scheduled=${JSON.stringify(slot)};`:''}
  checkoutId='fixture-order';$('custName').value='Fixture Person';$('authEmail').value='fixture@example.test';
  globalThis.ui={pay:()=> $('payBtn').onclick(),confirm:()=> $('confirmPayBtn').onclick(),invalidate:()=>invalidatePayment(),
    coupon:()=>{ $('couponInput').value='TEST';$('couponApply').onclick();},apply:()=>applyQuote(lastQuote),
    signOut:()=> $('signOut').onclick(),getCart:()=>cart,setCoupon:c=>{couponCode=c;},setCharging:v=>{chargeInFlight=v;}};
})();`;
 vm.runInContext(src.slice(0,src.indexOf('  loadSess(); renderAuth(); loadAllergens();'))+setup,context);
 return {ui:context.ui,el,calls,listeners,get mounted(){return mounted},get charged(){return charged},resolve:r=>pending(r)};
}
const flush=async()=>{for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));};
test('real page: missing/mismatched reservation never mounts Stripe or fulfils',async()=>{
 for(const reply of [{orderToken:'token',clientSecret:'secret'},{...response(),points:{...response().points,pointsReserved:122}}]){
  const h=harness({reply});h.ui.pay();await flush();assert.equal(h.mounted,0);assert.equal(h.charged,0);
  assert.equal(h.calls.some(c=>c.fn==='process-order'),false);
  assert.equal(h.calls.some(c=>c.fn==='points'&&c.body.action==='release'),true);
  assert.equal(h.el('payMsg').textContent,points.notConfirmed);
 }
});
test('real page: exact reservation permits card; extras and request match app',async()=>{
 const h=harness();h.ui.pay();await flush();assert.equal(h.mounted,1);assert.equal(h.charged,0);
 const body=h.calls.find(c=>c.fn==='create-payment-intent').body;
 assert.deepEqual(body.points,request);assert.equal(body.amount,520);
 assert.deepEqual({...body.order,delivery_time:example.body.order.delivery_time},JSON.parse(JSON.stringify(example.body.order)));
 h.ui.confirm();await flush();assert.equal(h.charged,1);assert.match(h.el('checkout').innerHTML,/\+52 points earned/);
});
test('real page: a scheduled slot is sent as the true instant, not the wall-clock stamp',async()=>{
 const h=harness({slot:{label:'Fri, 5:30 PM',iso:'2026-10-16T17:30:00.000Z'}});h.ui.pay();await flush();
 assert.equal(h.calls.find(c=>c.fn==='create-payment-intent').body.order.delivery_time,'2026-10-16T16:30:00.000Z');
});
test('real page: stale response releases reservation without mounting payment',async()=>{
 const h=harness({defer:true});h.ui.pay();await flush();h.ui.invalidate();h.resolve(response());await flush();
 assert.equal(h.mounted,0);assert.equal(h.calls.some(c=>c.fn==='points'&&c.body.action==='release'),true);
});
test('real page: editing the basket after the hold releases it',async()=>{
 const h=harness();h.ui.pay();await flush();assert.equal(h.mounted,1);
 h.ui.invalidate();await flush();
 const rel=h.calls.filter(c=>c.fn==='points'&&c.body.action==='release');
 assert.equal(rel.length,1);assert.equal(rel[0].body.orderToken,'fixture-token');assert.equal(rel[0].headers.Authorization,'Bearer fixture-jwt');
});
test('real page: leaving the page releases the hold (keepalive), but never mid-payment',async()=>{
 const h=harness();h.ui.pay();await flush();
 h.ui.setCharging(true);h.listeners.pagehide.forEach(f=>f());await flush();
 assert.equal(h.calls.some(c=>c.fn==='points'&&c.body.action==='release'),false);
 h.ui.setCharging(false);h.listeners.pagehide.forEach(f=>f());await flush();
 const rel=h.calls.filter(c=>c.fn==='points'&&c.body.action==='release');
 assert.equal(rel.length,1);assert.equal(rel[0].keepalive,true);
});
test('real page: guest and member without rewards retain order-pay shape',async()=>{
 for(const guest of [true,false]){
  const h=harness({guest,selected:false});h.ui.pay();await flush();assert.equal(h.mounted,1);
  const body=h.calls.find(c=>c.fn==='order-pay').body;assert.equal('points' in body,false);assert.equal('redeem' in body,false);
  assert.equal('guest' in body,guest);assert.equal(h.calls.some(c=>c.fn==='create-payment-intent'),false);
  if(guest){h.ui.confirm();await flush();assert.match(h.el('checkout').innerHTML,/Sign in with this email to see and spend your points\./);}
 }
});
// 3d: the request the page sends for a guest checkout, and for a signed-in
// checkout without points, must be byte-for-byte what web origin/main sends.
let mainSource=null;
try{mainSource=execFileSync('git',['show','origin/main:src/pages/order/index.astro'],{cwd:new URL('..',import.meta.url),encoding:'utf8'}).split('<script is:inline>\n')[1].split('</script>')[0];}catch(_e){}
test('real page: non-points checkout requests are byte-identical to origin/main',{skip:!mainSource&&'origin/main not available'},async()=>{
 for(const guest of [true,false]){
  for(const slot of [null,{label:'Fri, 5:30 PM',iso:'2026-10-16T17:30:00.000Z'}]){
   const sent=async src=>{const h=harness({src,guest,selected:false,slot});h.ui.pay();await flush();
    return JSON.stringify(h.calls.map(c=>({url:c.url,method:c.method,headers:c.headers,keepalive:!!c.keepalive,body:c.rawBody})));};
   const before=await sent(mainSource), after=await sent(source);
   assert.match(before,/\/order-pay"/);
   assert.equal(after,before,`guest=${guest} slot=${!!slot}`);
  }
 }
});
test('real page: coupon and points are mutually exclusive; sign-out clears selections',async()=>{
 const h=harness();h.ui.coupon();assert.equal(h.el('couponMsg').textContent,points.xorCoupon);
 h.ui.setCoupon('TEST');h.ui.apply();assert.match(h.el('redeemBox').innerHTML,new RegExp(points.xorCoupon));
 assert.doesNotMatch(h.el('redeemBox').innerHTML,/data-pplus/);
 h.ui.pay();await flush();assert.equal(h.el('payMsg').textContent,points.xorCoupon);
 assert.equal(h.calls.some(c=>c.fn==='create-payment-intent'||c.fn==='order-pay'),false);
 h.ui.signOut();assert.equal(h.ui.getCart()[0].pointsUnits,undefined);
});
test('real page: the panel uses the app wording ("Using 300 of 850 points")',async()=>{
 const coffee={label:'Coffee',cost:300,productIds:[],departmentIds:[21]};
 const s850={...status,balance:850,available:850,rewards:[{...status.rewards[0],name:'Coffee',pointsCost:300}]};
 const h=harness({lv:[coffee],pts:s850});
 h.ui.getCart()[0].pointsLabel='Coffee';h.ui.getCart()[0].pointsEach=300;h.ui.apply();
 const html=h.el('redeemBox').innerHTML;
 assert.match(html,/Points rewards/);assert.match(html,/Using 300 of 850 points/);assert.match(html,/300 points each/);
 assert.match(html,/Points cover the item itself\. Paid extras are charged as usual\./);
 h.ui.getCart()[0].pointsUnits=0;h.ui.apply();assert.match(h.el('redeemBox').innerHTML,/850 points available/);
});
test('real page: #81 excluded product gets no offer',async()=>{
 const h=harness({selected:false,lv:[{...levels[0],excludeProductIds:[511]}]});h.ui.apply();
 assert.doesNotMatch(h.el('redeemBox').innerHTML,/data-pplus/);
 assert.match(h.el('redeemBox').innerHTML,/Nothing in your basket can be paid for with points\. Rewards: fixture reward 123\./);
});

test('real page: fully points-paid order requires confirmation before processing',async()=>{
 const reply=response();delete reply.clientSecret;
 const h=harness({free:true,reply});h.ui.pay();await flush();
 assert.equal(h.calls.find(c=>c.fn==='create-payment-intent').body.amount,0);
 assert.equal(h.calls.find(c=>c.fn==='create-payment-intent').body.order.payment.amount,0);
 assert.equal(h.calls.some(c=>c.fn==='process-order'),true);
 assert.equal(h.mounted,0);assert.equal(h.charged,0);
 assert.match(h.el('checkout').innerHTML,/Order placed/);
 assert.doesNotMatch(h.el('checkout').innerHTML,/points earned/);
 const bad=harness({free:true,reply:{orderToken:'token'}});bad.ui.pay();await flush();
 assert.equal(bad.calls.some(c=>c.fn==='process-order'),false);
});
