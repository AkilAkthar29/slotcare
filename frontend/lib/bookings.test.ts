import { test } from 'node:test';
import assert from 'node:assert/strict';
import { api, ApiError } from './api';

test('booking requests use session credentials and the CSRF token rotated by login', async()=>{
 const original=globalThis.fetch;
 const calls: {url:string; options:RequestInit|undefined}[]=[];
 globalThis.fetch=async(input,options)=>{
  calls.push({url:String(input),options});
  const data=String(input).includes('session')?{user:null,csrfToken:'initial-token'}:String(input).includes('login')?{user:{username:'jamie',name:'Jamie Davis'},csrfToken:'rotated-token'}:{id:'1',slotId:123};
  return new Response(JSON.stringify(data),{status:200});
 };
 try{
  await api.login('jamie','demo-password'); await api.book(123);
  const booking=calls.at(-1)!;
  assert.equal(booking.url,'/api/appointments/');
  assert.equal(booking.options?.credentials,'same-origin');
  assert.equal(new Headers(booking.options?.headers).get('X-CSRFToken'),'rotated-token');
  assert.deepEqual(JSON.parse(String(booking.options?.body)),{slotId:123});
 }finally{globalThis.fetch=original;}
});

test('rescheduling surfaces API conflicts without sending a cancellation request',async()=>{
 const original=globalThis.fetch;const calls:string[]=[];
 globalThis.fetch=async(input)=>{calls.push(String(input));return new Response(JSON.stringify({detail:'Slot already booked.'}),{status:409});};
 try{
  await assert.rejects(api.reschedule('12',456),(error:unknown)=>error instanceof ApiError&&error.status===409&&error.message==='Slot already booked.');
  assert.deepEqual(calls,['/api/appointments/12/reschedule/']);
 }finally{globalThis.fetch=original;}
});
