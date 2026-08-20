const {sendJson, saveStore, adminOk, nowMs} = require('../../lib/store');
module.exports = function handler(req,res){
  if(req.method!=='POST') return sendJson(res,405,{error:'method_not_allowed'});
  if(!adminOk(req)) return sendJson(res,401,{error:'unauthorized'});
  saveStore({players:{},events:[],created_at:nowMs()});
  sendJson(res,200,{ok:true});
};
