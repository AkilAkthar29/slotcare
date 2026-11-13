import type { TimeSlot } from './bookings';
export type Region = { id: number; city: string; area: string; aliases: string[] };
export type Clinic = { id: number; name: string; address: string; fee: number; region: Region | null; is_active: boolean };
export type Doctor = { id: string; name: string; specialty: string; clinic: string; fee: number; initials: string; color: string; experience: number; rating: string; bio: string; region: Region | null; available: boolean; acceptingAppointments: boolean; clinics: Clinic[]; nextAvailable: TimeSlot | null };
export function displayDate(date: string) { return new Date(date+'T12:00:00').toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'}); }

export function timeOrder(time: string) { const [hours, minutes] = time.slice(0,5).split(':').map(Number); return (hours % 12 + (time.endsWith('PM') ? 12 : 0))*60+minutes; }
