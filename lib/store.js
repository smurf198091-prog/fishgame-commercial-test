const fs = require('fs');
const crypto = require('crypto');
const STORE_PATH = '/tmp/fishgame-commercial-test-store.json';
const sessions = global.__fishSessions || (global.__fishSessions = new Map());
const rates = global.__fishRates || (global.__fishRates = new Map());
function nowMs(){ return Date.now(); }
function sendJson(res,status,body){ res.statusCode=status; res.setHeader('Content-Type','application/json; charset=utf-8'); res.setHeader('Cache-Control','no-store'); res.end(JSON.stringify(body,null,2)); }
function readBody(req){ return new Promise(resolve=>{ let data=''; req.on('data',c=>{ data+=c; if(data.length>65536) req.destroy(); }); req.on('end',()=>{ try{resolve(data?JSON.parse(data):{})}catch{resolve({})} }); req.on('error',()=>resolve({})); }); }
function loadStore(){ try{return JSON.parse(fs.readFileSync(STORE_PATH,'utf8'))}catch{return {players:{},events:[],created_at:nowMs()}} }
function saveStore(store){ fs.writeFileSync(STORE_PATH, JSON.stringify(store)); }
function ipOf(req){ const xf=req.headers['x-forwarded-for']; return String(Array.isArray(xf)?xf[0]:(xf||req.socket.remoteAddress||'unknown')).split(',')[0].trim(); }
function rateOk(key,limit,windowMs){ const now=Date.now(); const q=rates.get(key)||[]; while(q.length && now-q[0]>windowMs) q.shift(); if(q.length>=limit) return false; q.push(now); rates.set(key,q); return true; }
function adminOk(req){ const token=process.env.ADMIN_TOKEN||''; if(token.length<16) return false; const got=Buffer.from(String(req.headers['x-admin-token']||'')); const expected=Buffer.from(token); if(got.length!==expected.length) return false; return crypto.timingSafeEqual(got, expected); }
function newSession(){ const token=crypto.randomBytes(24).toString('base64url'); sessions.set(token, nowMs()+2*60*60*1000); return token; }
function sessionOk(req){ const token=String(req.headers['x-game-session']||''); return Boolean(token && sessions.get(token)>nowMs()); }
function summary(store){ const events=store.events||[]; const players=Object.values(store.players||{}); return {players:players.length,fires:events.filter(e=>e.type==='fire').length,captures:events.filter(e=>e.type==='capture').length,events:events.length}; }
module.exports={nowMs,sendJson,readBody,loadStore,saveStore,ipOf,rateOk,adminOk,newSession,sessionOk,summary};
