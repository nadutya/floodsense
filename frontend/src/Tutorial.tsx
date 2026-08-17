import {useLayoutEffect,useState} from 'react'
import type {CSSProperties} from 'react'

type Step={target?:string;title:string;text:string;side?:boolean;mapNote?:boolean}
const steps:Step[]=[
 {title:'FloodSense',text:'A drainage digital twin that can be adapted to any city. It follows a storm through the local network, finds the drains most likely to fail and shows what a maintenance crew could prevent.'},
 {target:'.map-wrap',mapNote:true,title:'This demo: West Oxford',text:'Here we use a small demonstration network in Oxford. Each coloured dot is a connected street drain. Click one for details; drag the map or use the controls to move around.'},
 {target:'.map-wrap',mapNote:true,title:'How the model fills a drain',text:'Rain runs off each drain’s surrounding streets and enters its local storage. Leaves reduce the inlet capacity. When water arrives faster than the drain can carry it away, storage fills and water reaches the street. Part stays on the surface; part continues to the next drain downhill.'},
 {target:'.route-line',mapNote:true,title:'Why the emergency route matters',text:'The dotted line is an emergency access route to the clinic. It does not change how water flows. It changes what matters first: a drain that could block this route receives a higher response priority.'},
 {target:'footer',title:'Make it rain',text:'Choose the rainfall rate, then press play. A new rate changes what happens next—it never rewrites what already happened. The three speeds only make the clock run faster or slower.'},
 {target:'.sensor-stack',side:true,title:'Look inside a drain',text:'LVL reports water depth; RX counts the readings received so far. CAM watches the grate for leaves. Confidence shows how clearly the camera can recognise what it sees.'},
 {target:'.recommendation',side:true,title:'Send help',text:'When this drain needs attention first, a crew button appears. Clearing it opens the inlet again, then the whole forecast updates around that change.'},
 {target:'.failure-log',title:'Keep the history',text:'Every overflow stays in this strip, including repeat events. Scroll sideways to go back. After a crew visit, the result note shows the estimated water kept off the street.'}
]

export function Tutorial({onClose}:{onClose:()=>void}){
 const[index,setIndex]=useState(0),[box,setBox]=useState<DOMRect|null>(null),step=steps[index]
 useLayoutEffect(()=>{let timer=0;const el=step.target?document.querySelector(step.target):null;const update=()=>setBox(el?.getBoundingClientRect()??null);if(el&&innerWidth<=750){el.scrollIntoView({behavior:'smooth',block:'center'});timer=window.setTimeout(update,320)}else update();addEventListener('resize',update);addEventListener('scroll',update,{passive:true});return()=>{clearTimeout(timer);removeEventListener('resize',update);removeEventListener('scroll',update)}},[step])
 const style=box?{left:Math.max(8,box.left-6),top:Math.max(8,box.top-6),width:box.width+12,height:box.height+12}:undefined
 const cardClass=!box?'center':step.side?'left':step.mapNote?'map-note':box.top>innerHeight*.62?'above':box.left>innerWidth*.58?'left':'right'
 return <div className="tour" role="dialog" aria-modal="true" aria-label="FloodSense tutorial">
  {box&&<div className="tour-focus" style={style}/>} {!box&&<div className="tour-shade"/>}
  <section className={`tour-card ${cardClass}`} style={box?{'--focus-left':`${box.left}px`,'--focus-top':`${box.top}px`,'--focus-right':`${innerWidth-box.right}px`,'--focus-bottom':`${innerHeight-box.bottom}px`} as CSSProperties:undefined}>
   <div className="tour-count">{String(index+1).padStart(2,'0')} / {String(steps.length).padStart(2,'0')}</div><h2>{step.title}</h2><p>{step.text}</p>
   <div className="tour-actions"><button className="tour-skip" onClick={onClose}>Skip</button><div>{index>0&&<button onClick={()=>setIndex(index-1)}>Back</button>}<button className="tour-next" onClick={()=>index===steps.length-1?onClose():setIndex(index+1)}>{index===steps.length-1?'Start exploring':'Next'} →</button></div></div>
  </section>
 </div>
}
