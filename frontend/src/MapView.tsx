import {useRef,useState} from 'react'
import type {PointerEvent,WheelEvent} from 'react'
import type {Asset,Drain,DrainState} from './types'

type Props={drains:Drain[];assets:Asset[];states:DrainState[];selected:string;priorityId:string|null;onSelect:(id:string)=>void}
const B={west:-1.274,east:-1.251,north:51.757,south:51.746}
const point=(lon:number,lat:number)=>({x:(lon-B.west)/(B.east-B.west)*1200,y:(B.north-lat)/(B.north-B.south)*760})
const colors={normal:'#497466',watch:'#c5a03c',high:'#d17636',critical:'#bd4439'}

export function MapView({drains,assets,states,selected,priorityId,onSelect}:Props){
 const[view,setView]=useState({x:-60,y:-35,scale:1.12}),[hover,setHover]=useState<string|null>(null)
 const drag=useRef<{x:number;y:number;vx:number;vy:number}|null>(null)
 const wheel=(e:WheelEvent)=>{e.preventDefault();setView(v=>({...v,scale:Math.max(1,Math.min(2.8,v.scale*(e.deltaY<0?1.14:.88)))}))}
 const down=(e:PointerEvent)=>{(e.currentTarget as Element).setPointerCapture(e.pointerId);drag.current={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y}}
 const move=(e:PointerEvent)=>{if(!drag.current)return;const d=drag.current;setView(v=>({...v,x:d.vx+(e.clientX-d.x)/v.scale,y:d.vy+(e.clientY-d.y)/v.scale}))}
 const up=()=>{drag.current=null}
 const selectedDrain=drains.find(d=>d.id===hover),selectedState=states.find(s=>s.id===hover)
 return <div className="native-map" onWheel={wheel} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
  <svg viewBox="0 0 1200 760" role="application" aria-label="Interactive Oxford drainage map">
   <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
    <image href="/oxford-fallback.svg" width="1200" height="760"/>
    {assets.filter(a=>a.kind==='route'&&a.coordinates).map(a=><g key={a.id}><polyline className="route-line" points={a.coordinates!.map(c=>{const p=point(c[0],c[1]);return`${p.x},${p.y}`}).join(' ')}/><text className="route-label" x="330" y="500">EMERGENCY ACCESS ROUTE</text></g>) }
    {assets.filter(a=>a.lon&&a.lat).map(a=>{const p=point(a.lon!,a.lat!);return <g key={a.id} className="svg-asset" transform={`translate(${p.x} ${p.y})`}><rect x="-12" y="-12" width="24" height="24"/><text x="18" y="4">{a.kind==='clinic'?'CLINIC':'SCHOOL'} · {a.name}</text><text textAnchor="middle" y="5" className="asset-symbol">{a.kind==='clinic'?'+':'S'}</text></g>})}
    {drains.map(d=>{const p=point(d.lon,d.lat),s=states.find(x=>x.id===d.id),active=d.id===selected;return <g key={d.id} className={`svg-drain ${active?'selected':''} ${d.id===priorityId?'priority':''}`} transform={`translate(${p.x} ${p.y})`} onPointerDown={e=>e.stopPropagation()} onClick={()=>onSelect(d.id)} onMouseEnter={()=>setHover(d.id)} onMouseLeave={()=>setHover(null)}>
     <circle className="priority-wave" r="22"/><circle className="priority-wave priority-wave-late" r="22"/><circle className="drain-target" r="31"/><circle className="drain-ring" r={active?22:18}/><circle className="drain-core" r={active?13:11} fill={colors[s?.risk||'normal']}/><text className="drain-id" y="-28" textAnchor="middle">{d.id}</text><text className="drain-eta" y="35" textAnchor="middle">{s?.minutes_to_overflow==null?(s?.overflow_m3?'NOW':'—'):`${s.minutes_to_overflow} min`}</text>
    </g>})}
   </g>
  </svg>
  {hover&&selectedDrain&&<div className="native-tooltip"><b>{hover}</b><span>{selectedDrain.name}</span><em>{selectedState?.fill_pct}% full · {selectedState?.risk}</em></div>}
  <div className="native-controls" onPointerDown={e=>e.stopPropagation()}><button onClick={()=>setView(v=>({...v,scale:Math.min(2.8,v.scale*1.2)}))}>+</button><button onClick={()=>setView(v=>({...v,scale:Math.max(1,v.scale/1.2)}))}>−</button><button onClick={()=>setView({x:-60,y:-35,scale:1.12})}>⌂</button></div>
 </div>
}
