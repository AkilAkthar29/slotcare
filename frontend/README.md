# SlotCare frontend

Next.js + TypeScript + Tailwind connected to Django REST Framework. See [the root README](../README.md) for startup, optional sample seed, credentials, directory coverage, and the two-minute sample.

```powershell
Set-Location D:\slotcare\slotcare\frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000 with Django running on port 8000. `/patient` and `/doctor` have separate login experiences. The searchable neighbourhood dropdown is populated by Django Regions; All areas is the default. Booking confirmations use the chosen slot's clinic/address and fee. No bookings are stored in localStorage.
