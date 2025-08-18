import express from 'express'; import cors from 'cors'; import fetch from 'node-fetch';
import { Queue } from 'bullmq';
const app = express(); app.use(cors()); app.use(express.json());
const GC_BASE = process.env.GC_BASE!; const GC_TOKEN = process.env.GC_TOKEN;
const q = new Queue('actions',{ connection:{ host: process.env.REDIS_HOST||'127.0.0.1', port: +(process.env.REDIS_PORT||6379) }});

// simple proxy helpers
async function forward(path:string, init: any){ 
  const res = await fetch(`${GC_BASE}${path}`, { ...init, headers:{'Content-Type':'application/json', ...(GC_TOKEN?{Authorization:`Bearer ${GC_TOKEN}`}:{}) }});
  if (!res.ok) throw new Error(await res.text()); return res.json();
}

// Guardian Codex API bridge
app.post('/codexify', (req,res)=>forward('/codexify',{method:'POST',body:JSON.stringify(req.body)}).then(x=>res.json(x)).catch(e=>res.status(500).send(String(e))));
app.post('/log', (req,res)=>forward('/log',{method:'POST',body:JSON.stringify(req.body)}).then(x=>res.json(x)).catch(e=>res.status(500).send(String(e))));
app.post('/summarize', (req,res)=>forward('/summarize',{method:'POST',body:JSON.stringify(req.body)}).then(x=>res.json(x)).catch(e=>res.status(500).send(String(e))));
app.get('/whoami', (_req,res)=>forward('/whoami',{method:'GET'}).then(x=>res.json(x)).catch(e=>res.status(500).send(String(e))));
app.post('/profile', (req,res)=>forward('/profile',{method:'POST',body:JSON.stringify(req.body)}).then(x=>res.json(x)).catch(e=>res.status(500).send(String(e))));

// Action layer endpoints
app.post('/tools/execute', async (req,res)=>{
  const job = await q.add('tool', req.body, { removeOnComplete:true, removeOnFail:true });
  res.json({ jobId: job.id });
});
app.get('/jobs/:id', async (req,res)=>{
  const job = await q.getJob(req.params.id); if(!job) return res.status(404).send('not found');
  const st = await job.getState(); const r = await job.getReturnValue(); res.json({ state: st, result: r });
});

app.listen(process.env.PORT||3001, ()=>console.log('bridge+actions on :' + (process.env.PORT||3001)));
