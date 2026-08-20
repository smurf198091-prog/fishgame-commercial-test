const {sendJson, readBody, loadStore, saveStore, ipOf, rateOk, sessionOk, nowMs} = require('../lib/store');
module.exports = async function handler(req,res){
  if(req.method!=='POST') return sendJson(res,405,{error:'method_not_allowed'});
  const ip=ipOf(req);
  if(!sessionOk(req) || !rateOk('event:'+ip,120,60000)) return sendJson(res,401,{error:'unauthorized_or_rate_limited'});
  const data=await readBody(req); const store=loadStore();
  const type=String(data.type||'unknown').slice(0,40); const playerId=String(data.player_id||'local-player').slice(0,80);
  const coin=Number.isFinite(Number(data.coin))?Number(data.coin):0; const ts=Number.isFinite(Number(data.ts))?Number(data.ts):nowMs();
  store.players[playerId]=store.players[playerId]||{player_id:playerId,coin:0,fires:0,captures:0,status:'active',created_at:ts,updated_at:ts};
  const player=store.players[playerId]; player.coin=coin; player.updated_at=ts; if(type==='fire') player.fires+=1; if(type==='capture') player.captures+=1;
  store.events.push({id:store.events.length+1,ts,type,player_id:playerId,payload:data}); if(store.events.length>500) store.events=store.events.slice(-500);
  saveStore(store); sendJson(res,200,{ok:true});
};
