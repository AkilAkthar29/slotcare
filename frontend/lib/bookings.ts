import type { Clinic } from './doctors';
export type Booking = { id: string; doctorId: string; doctorName: string; specialty: string; slotId: number; date: string; time: string; status: 'confirmed' | 'cancelled' | 'completed'; createdAt: string; clinic: Clinic; fee: number };
export type TimeSlot = { id: number; doctorId: string; date: string; time: string; booked: boolean; is_active: boolean; clinic: Clinic };
export type DoctorBooking = Booking & { patientName: string; canComplete: boolean };
