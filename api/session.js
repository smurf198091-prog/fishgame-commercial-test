const {sendJson, ipOf, rateOk, newSession} = require('../lib/store');
module.exports = function handler(req,res){
  if(req.method!=='GET') return sendJson(res,405,{error:'method_not_allowed'});
  const ip=ipOf(req);
  if(!rateOk('session:'+ip,30,60000)) return sendJson(res,429,{error:'rate_limited'});
  sendJson(res,200,{token:newSession(),expires_in:7200});
};
