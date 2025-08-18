import React, { useEffect, useRef, useState } from 'react';
import { savePrimary, getPins } from '@/hooks/useSaveRitual';

export function SaveControl({ payload, projectSlug }:{
  payload:{ markdown:string; threadId?:string; turnIndex?:number };
  projectSlug:string;
}) {
  const [open,setOpen]=useState(false); const [pins,setPins]=useState<string[]>([]);
  const btnRef=useRef<HTMLButtonElement|null>(null);
  useEffect(()=>{ getPins().then(setPins).catch(()=>{}); },[]);
  useEffect(()=>{
    const onKey=(e:KeyboardEvent)=>{ if ((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='s'){ e.preventDefault(); onSave(); } };
    window.addEventListener('keydown',onKey); return ()=>window.removeEventListener('keydown',onKey);
  },[]);
  async function onSave(target?:string){
    const res = await savePrimary({ projectSlug: target||projectSlug, ...payload, autoFormat:true });
    // simple snackbar
    (window as any).alert?.(`Saved → ${res.path}`);
    setOpen(false);
  }
  return (
    <div style={{display:'inline-flex',gap:6,alignItems:'center',position:'relative'}}>
      <button onClick={()=>onSave()} aria-label="Save (⌘S)" style={btn()}>Save</button>
      <button ref={btnRef} onClick={()=>setOpen(v=>!v)} aria-label="Choose pinned project" style={caret()}>▾</button>
      {open && (
        <div role="menu" style={menu()}>
          {pins.length===0 && <div style={empty()}>No pins yet</div>}
          {pins.map(pid=>(
            <button key={pid} role="menuitem" style={row()} onClick={()=>onSave(pid)}>{pid}</button>
          ))}
          <div style={{borderTop:'1px solid rgba(255,255,255,.1)',marginTop:6,paddingTop:6}}>
            <button role="menuitem" style={row('muted')} onClick={()=>((window as any).openSettings?.('pins'))}>Manage Pins…</button>
          </div>
        </div>
      )}
    </div>
  );
}
const btn = ()=>({ padding:'6px 10px', borderRadius:10, border:0, background:'rgba(99,102,241,0.9)', color:'#fff', cursor:'pointer' });
const caret = ()=>({ padding:'6px 8px', borderRadius:10, border:'1px solid rgba(255,255,255,.2)', background:'transparent', color:'#fff', cursor:'pointer' });
const menu = ()=>({ position:'absolute' as const, top:34, right:0, background:'rgba(0,0,0,.85)', color:'#fff', border:'1px solid rgba(255,255,255,.15)', borderRadius:10, padding:6, minWidth:180, zIndex:999 });
const row = (kind?:'muted')=>({ display:'block', width:'100%', textAlign:'left' as const, padding:'6px 8px', borderRadius:8, border:0, background:'transparent', color: kind==='muted'?'#ddd':'#fff', cursor:'pointer' });
const empty = ()=>({ fontSize:12, opacity:.8, padding:'6px 8px' });




