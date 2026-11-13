import type { Clinic, Doctor, Region } from './doctors';
import type { Booking, DoctorBooking, TimeSlot } from './bookings';
export type Patient = { username: string; name: string; role: 'patient' | 'doctor' };
type Session = { user: Patient | null; csrfToken: string };
let csrfToken = '';
export class ApiError extends Error { constructor(message: string, public status: number) { super(message); } }
async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/${path}`, { method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(body === undefined ? {} : {'X-CSRFToken': csrfToken}) }, ...(body === undefined ? {} : {body: JSON.stringify(body)}) });
  } catch { throw new ApiError('Cannot connect to SlotCare. Check that both apps are running.', 0); }
  const data = await response.json().catch(()=>null);
  if (!response.ok) {
    const message = data?.detail || (data ? Object.values(data).flat().join(' ') : 'The API is unavailable. Check that Django is running.');
    throw new ApiError(typeof message === 'string' ? message : 'Unable to complete this request.', response.status);
  }
  return data as T;
}
export const api = {
  session: async () => { const data = await request<Session>('auth/session/'); csrfToken=data.csrfToken; return data.user; },
  login: async (username:string,password:string,portal:'patient'|'doctor'='patient') => { await api.session(); const data=await request<Session>('auth/login/',{username,password,portal});csrfToken=data.csrfToken;return data.user!; },
  logout: async () => { const data=await request<Session>('auth/logout/',{});csrfToken=data.csrfToken; },
  doctors: (filters?:{city?:string;region?:string;specialty?:string;q?:string;available?:string}) => {const params=new URLSearchParams();Object.entries(filters||{}).forEach(([k,v])=>{if(v)params.set(k,v);});return request<Doctor[]>(`doctors/${params.size?'?'+params:''}`);},
  doctor: (id:string) => request<Doctor>(`doctors/${encodeURIComponent(id)}/`),
  regions: () => request<Region[]>('regions/'),
  doctorProfile: () => request<Doctor>('doctor-portal/profile/'),
  updateDoctor: (settings:{acceptingAppointments?:boolean}) => request<Doctor>('doctor-portal/profile/',settings),
  doctorClinics: () => request<Clinic[]>('doctor-portal/clinics/'),
  saveClinic: (clinic:{clinicId?:number;name?:string;address?:string;fee?:number;regionId?:number}) => request<Clinic>('doctor-portal/clinics/',clinic),
  doctorSlots: () => request<TimeSlot[]>('doctor-portal/slots/'),
  addSlot: (date:string,time:string,clinicId:number) => request<TimeSlot>('doctor-portal/slots/',{date,time,clinicId}),
  closeSlot: (slotId:number) => request<{detail:string}>('doctor-portal/close-slot/',{slotId}),
  doctorAppointments: () => request<DoctorBooking[]>('doctor-portal/appointments/'),
  completeVisit: (appointmentId:string) => request<DoctorBooking>('doctor-portal/complete/',{appointmentId:Number(appointmentId)}),
  slots: (doctorId:string,clinicId?:string) => request<TimeSlot[]>(`doctors/${encodeURIComponent(doctorId)}/slots/${clinicId?'?clinic='+encodeURIComponent(clinicId):''}`),
  appointments: () => request<Booking[]>('appointments/'),
  book: (slotId:number) => request<Booking>('appointments/',{slotId}),
  cancel: (id:string) => request<Booking>(`appointments/${encodeURIComponent(id)}/cancel/`,{}),
  reschedule: (id:string,slotId:number) => request<Booking>(`appointments/${encodeURIComponent(id)}/reschedule/`,{slotId}),
};
