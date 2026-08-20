const {sendJson, nowMs} = require('../lib/store');
module.exports = function handler(req,res){
  sendJson(res,200,{status:'ok',env:process.env.APP_ENV||'commercial-test',runtime:'vercel-serverless',admin_token_configured:(process.env.ADMIN_TOKEN||'').length>=16,payments_enabled:false,time_ms:nowMs()});
};
