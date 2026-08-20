const {sendJson, loadStore, adminOk, summary} = require('../../lib/store');
module.exports = function handler(req,res){
  if(req.method!=='GET') return sendJson(res,405,{error:'method_not_allowed'});
  if(!adminOk(req)) return sendJson(res,401,{error:'unauthorized'});
  const store=loadStore();
  const players=Object.values(store.players||{}).sort((a,b)=>b.updated_at-a.updated_at).slice(0,200);
  const events=(store.events||[]).slice(-80).reverse();
  sendJson(res,200,{status:'ok',summary:summary(store),players,events});
};
