import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'SlotCare · Care that fits your day', description: 'Find available doctors in your area, book a visit, or manage your clinic schedule.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
