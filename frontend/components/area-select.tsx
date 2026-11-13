'use client';
import { useEffect, useId, useRef, useState } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import type { Region } from '@/lib/doctors';

export default function AreaSelect({regions,value,onChange,allowAll=true,label='Neighbourhood'}:{regions:Region[];value:string;onChange:(value:string)=>void;allowAll?:boolean;label?:string}) {
 const id=useId(); const root=useRef<HTMLDivElement>(null);
 const [open,setOpen]=useState(false); const [search,setSearch]=useState(''); const [active,setActive]=useState(0);
 const matches=regions.filter(r=>[r.area,...(r.aliases||[])].join(' ').toLowerCase().includes(search.toLowerCase()));
 const options=[...(allowAll&&!search?[{id:'',label:'All areas'}]:[]),...matches.map(r=>({id:String(r.id),label:r.area}))];
 const selected=regions.find(r=>String(r.id)===value)?.area||(allowAll?'All areas':'Select an area');
 useEffect(()=>{function outside(e:PointerEvent){if(!root.current?.contains(e.target as Node))setOpen(false);}document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside);},[]);
 function choose(index:number){if(options[index]){onChange(options[index].id);setOpen(false);setSearch('');}}
 return <div className="area-combobox" ref={root}><label htmlFor={id}>{label}</label><div className="area-input"><Search size={15}/><input id={id} role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={id+'-list'} aria-activedescendant={open&&options[active]?`${id}-${active}`:undefined} autoComplete="off" value={open?search:selected} placeholder="Search Chennai neighbourhoods" onFocus={()=>{setOpen(true);setSearch('');setActive(0);}} onChange={e=>{setSearch(e.target.value);setOpen(true);setActive(0);}} onBlur={e=>{if(!root.current?.contains(e.relatedTarget as Node))setOpen(false);}} onKeyDown={e=>{if(e.key==='Escape'){setOpen(false);return;}if(e.key==='Tab'){setOpen(false);return;}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();setOpen(true);setActive(a=>Math.max(0,Math.min(options.length-1,a+(e.key==='ArrowDown'?1:-1))));}if(e.key==='Enter'&&open){e.preventDefault();choose(active);}}}/><ChevronDown size={14}/></div>{open&&<div role="listbox" id={id+'-list'} className="area-options" aria-label="Chennai neighbourhoods">{options.length?options.map((option,index)=><div key={option.id} role="option" id={`${id}-${index}`} aria-selected={option.id===value} className={index===active?'area-option highlighted':'area-option'} onMouseDown={e=>e.preventDefault()} onMouseEnter={()=>setActive(index)} onClick={()=>choose(index)}>{option.label}{option.id===value&&<span>Selected</span>}</div>):<p className="area-no-results">No matching neighbourhood. Your clinic administrator can add one.</p>}</div>}</div>;
}
