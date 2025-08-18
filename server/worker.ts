import { Worker, Job } from 'bullmq'; import fetch from 'node-fetch'; import fs from 'node:fs/promises';
const conn = { connection:{ host: process.env.REDIS_HOST||'127.0.0.1', port: +(process.env.REDIS_PORT||6379) } };

new Worker('actions', async (job: Job) => {
  const { type, args } = job.data as { type: string; args: any };
  if (type==='save_markdown') {
    // write to disk or forward to Codexify summarize
    return { ok:true };
  }
  if (type==='create_clickup_task') {
    // call ClickUp API with args; return task id
    return { ok:true, id:'task_123' };
  }
  if (type==='create_calendar_event') {
    // call calendar provider
    return { ok:true, id:'evt_123' };
  }
  return { ok:false, reason:'unknown tool' };
}, conn);
