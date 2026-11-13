'use client';
import { useState } from 'react';
import AreaSelect from './area-select';
import type { Clinic, Region } from '@/lib/doctors';

export type ClinicValues={clinicId?:number;name:string;address:string;fee:number;regionId:number};
export default function ClinicManager({clinics,regions,busy,onSave}:{clinics:Clinic[];regions:Region[];busy:boolean;onSave:(data:ClinicValues)=>Promise<boolean>}) {
 const [id,setId]=useState('');const [name,setName]=useState('');const [address,setAddress]=useState('');const [fee,setFee]=useState('');const [region,setRegion]=useState('');
 function edit(value:string){setId(value);const clinic=clinics.find(c=>String(c.id)===value);setName(clinic?.name||'');setAddress(clinic?.address||'');setFee(clinic?String(clinic.fee):'');setRegion(String(clinic?.region?.id||''));}
 return <form className="clinic-editor" onSubmit={async e=>{e.preventDefault();await onSave({...(id?{clinicId:Number(id)}:{}),name,address,fee:Number(fee),regionId:Number(region)});}}><label>Clinic<select aria-label="Edit clinic" value={id} onChange={e=>edit(e.target.value)}><option value="">Add a new clinic</option>{clinics.map(c=><option key={c.id} value={c.id}>{c.name} - {c.region?.area||'Area not set'}</option>)}</select></label><div className="clinic-form-row"><label>Clinic name<input required maxLength={160} value={name} onChange={e=>setName(e.target.value)}/></label><label>Consultation fee (INR)<input type="number" required min="0" step="1" max="2147483647" value={fee} onChange={e=>setFee(e.target.value)}/></label></div><AreaSelect label="Chennai neighbourhood" allowAll={false} regions={regions.filter(r=>r.city==='Chennai')} value={region} onChange={setRegion}/><label>Full street address<textarea required rows={2} value={address} onChange={e=>setAddress(e.target.value)} placeholder="Building, street and postcode"/></label><button className="secondary" disabled={busy||!region}>{id?'Save clinic':'Add clinic'}</button></form>;
}
