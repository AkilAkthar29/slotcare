# SlotCare

A doctor appointment booking app built with **Next.js, TypeScript, Tailwind CSS, Django REST Framework, and SQLite**.

Patients search Chennai doctors by neighbourhood, specialty, clinic, and availability. Doctors manage clinics, schedules, and visits through a separate portal. Bookings are stored in Django, not browser localStorage.

## Features

- Searchable directory of 207 Chennai neighbourhoods, including areas with no clinics.
- Combined area, specialty, text, and availability filters.
- Doctor cards with experience, rating, clinic, consultation fee, and next appointment.
- Multiple clinics per doctor, with clinic-specific addresses and fees.
- Booking, cancellation, and transactional rescheduling.
- Separate patient and doctor logins with backend ownership checks.
- Doctor slot publishing, blocking unbooked slots, and completing past visits.
- Django Admin for users, profiles, neighbourhoods, clinics, and appointments.

## Requirements

- Node.js 20.9 or newer and npm.
- Python 3.13 recommended; this workspace uses standard Windows Python.
- Two PowerShell terminals for local development.

## First-time setup

From the repository root:

```powershell
cd D:\slotcare\slotcare\backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Skip environment creation if `backend\.venv` already exists. The superuser command prompts for credentials; passwords are invisible while typing. No admin credentials are included in the repository.

Install frontend dependencies:

```powershell
cd D:\slotcare\slotcare\frontend
npm install
```

These commands use the environment's Python directly, so activation is optional. With standard Windows Python, you can activate it from `backend/` using `.\.venv\Scripts\Activate.ps1`, then run `python manage.py ...`. An environment created with MSYS2 Python may use `bin` instead of `Scripts`; use its actual executable rather than mixing Python installations.

## Run locally

**Terminal 1 - Django backend**

```powershell
cd D:\slotcare\slotcare\backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

**Terminal 2 - Next.js frontend**

```powershell
cd D:\slotcare\slotcare\frontend
npm run dev
```

| Page | URL |
| --- | --- |
| Website / doctor search | http://127.0.0.1:3000 |
| Patient login | http://127.0.0.1:3000/patient |
| Doctor login | http://127.0.0.1:3000/doctor |
| Django Admin | http://127.0.0.1:8000/admin/ |
| Doctor API | http://127.0.0.1:8000/api/doctors/ |

Keep both terminals running. Press **Ctrl+C** in each to stop them. Next.js proxies `/api/` to Django on port 8000; set `DJANGO_API_URL` before starting Next.js to use another backend address. Keep the frontend on port 3000 unless you also update Django's trusted CSRF origins.

## Patient and doctor accounts

Create users through **Django Admin ? Users ? Add**. Patient accounts need no staff privileges and must not be linked to a Doctor profile.

To enable a doctor login:

1. Create a user with a username and password.
2. Open **Doctors**, edit the intended profile, and select that user in the **User** field.
3. Save. Staff or superuser privileges are not required for the doctor portal.
4. Sign out of Admin, then log in at `/doctor` with those credentials.

Admin, patient, and doctor sessions share cookies within a browser profile. Use a regular and private window for simultaneous patient/doctor sessions, or sign out before switching roles. The eight profiles below do not automatically create login accounts.

## Optional fictional profiles and test slots

The project includes an explicit seed command for the eight requested fictional profiles. Normal startup never creates these records automatically.

```powershell
cd D:\slotcare\slotcare\backend
.\.venv\Scripts\python.exe manage.py seed_requested_doctors --experience 0 --rating 4.5
.\.venv\Scripts\python.exe manage.py update_requested_doctor_metadata
```

The first command reuses existing Chennai neighbourhoods and adds two slots per doctor for **tomorrow at 10:30 AM and 11:00 AM, Asia/Kolkata**. The second applies the supplied experience and rating values:

| Doctor | Specialty | Clinic | Area | Fee | Experience | Rating / 5 |
| --- | --- | --- | --- | --- | --- | --- |
| Dr. Nila Vetrivel | General Medicine | Blue Tamarind Clinic | Anna Nagar | INR 500 | 12 | 4.7 |
| Dr. Adhavan Ilanchezhian | Cardiology | Fernbank Heart Clinic | Adyar | INR 900 | 18 | 4.9 |
| Dr. Yazhini Thenmozhi | Dermatology | Copperleaf Skin Clinic | Velachery | INR 700 | 8 | 4.8 |
| Dr. Iniyan Arulnathan | Pediatrics | Little Banyan Clinic | Mogappair | INR 600 | 10 | 4.6 |
| Dr. Mithra Pazhanivel | Orthopedics | Pebble Grove Ortho Clinic | T. Nagar | INR 800 | 15 | 4.7 |
| Dr. Kavin Mutharasan | Neurology | Blue Kite Neuro Clinic | Tondiarpet | INR 900 | 16 | 4.8 |
| Dr. Oviya Senthamaran | ENT | Silver Finch ENT Clinic | Perungudi | INR 650 | 7 | 4.5 |
| Dr. Viyan Nallamuthu | Ophthalmology | Clear Fern Eye Clinic | Mylapore | INR 750 | 11 | 4.6 |

Names, ratings, and clinic details are fictional. Street addresses were not supplied and remain blank, with an address-pending message in the UI. No visible sample-data badge is displayed. Ratings use the existing rating field, and experience is stored as integer years.

Seeding is safe to repeat: existing records, edited fees, accounts, blocked slots, and bookings are preserved. Same-day reruns do not duplicate slots; later reruns add slots for the new tomorrow. Use `--dry-run` to validate without saving. The metadata command matches names and verifies fictional-profile markers before updating only those eight profiles.

A separate optional interview dataset remains available:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo --days 7 --include-past-visit
```

That command creates three additional fictional doctors, four clinics, and sample logins (`slotcare_demo_patient`, `slotcare_demo_doctor_1`, `_2`, `_3`; initial password `SlotCareDemo123!`). These accounts exist only after that command runs, and rerunning never resets an existing password. It is separate from the eight-profile dataset above.

## Chennai directory coverage

Neighbourhoods are stored in Django `Region` and loaded through `/api/regions/`, including places with no clinics. Administrators can edit names and searchable aliases in Admin. The UI defaults to **All areas** within Chennai.

The checked-in dataset contains **207 normalized neighbourhood names**, covering Chennai city and selected adjoining metro localities from its source lists. It is not an official GCC ward-boundary list or an exhaustive list of every informal colony. Area matching uses the clinic's saved neighbourhood; it does not calculate GPS distance.

Sources and full attribution are recorded in [the dataset README](backend/care/data/README.md): the pinned [Chennai neighbourhood coordinates dataset](https://github.com/yankarto/Chennai-neighborhood-coordinates-dataset/tree/49a56f4900a71e16733c59e1806b3837169a29e3), supplemented by [Areas of Chennai](https://en.wikipedia.org/w/index.php?title=Areas_of_Chennai&oldid=1376771538) and the [regional neighbourhood list](https://en.wikipedia.org/w/index.php?title=List_of_neighbourhoods_of_Chennai&oldid=1326017160). Only names and aliases are used, not the source coordinates. Runtime requests need no external dataset service.

## Booking rules and data preservation

- A doctor can practise at multiple clinics. Every slot links to its clinic and doctor.
- Availability requires an accepting doctor, an active clinic, and an active, unbooked future slot. Times use IST; later-today and later-date slots are supported.
- Result cards show the next slot at a clinic in the selected area. Confirmation and My Appointments show the booked clinic/address and fee.
- Database constraints prevent duplicate confirmed bookings for a slot and duplicate start times for a doctor across clinics.
- Cancelling retains history and releases the slot. Rescheduling is atomic: if the target fails, the original booking and fee remain intact.
- Fees are snapshotted when booking/rescheduling. Subsequent clinic fee changes do not rewrite existing booking fees.
- Doctors can manage only their own clinics, schedules, and visits; patients can access only their own appointments.
- Completed visits cannot be cancelled or rescheduled. Doctors may complete a confirmed visit only after its 30-minute appointment has ended.

Migration history is retained. Clinic migrations backfill existing slots while preserving account/password data, booking IDs, owners, status, and fees. Back up your SQLite database before applying migrations to an important local database. Local backups, database files, and environments are excluded from Git.

## Doctor Portal workflow

Add or edit a clinic's name, neighbourhood, full address, and consultation fee. Select the clinic when publishing slots, then turn **Accepting appointments** on. Close only unbooked slots; pausing availability does not cancel existing visits. Upcoming appointments and past visit history appear in the portal, with **Mark completed** for eligible visits.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/auth/session/` | Current user, role, and CSRF token |
| POST | `/api/auth/login/` | Username, password, and portal (`patient` or `doctor`) |
| POST | `/api/auth/logout/` | End session |
| GET | `/api/regions/` | Neighbourhoods; optional city and search |
| GET | `/api/doctors/` | Filters: city, area, region, specialty, q, available |
| GET | `/api/doctors/{id}/slots/` | Future slots; optional clinic/date/area filters |
| GET / POST | `/api/appointments/` | Own appointments / book with slotId |
| GET | `/api/appointments/{id}/` | Own appointment |
| POST | `/api/appointments/{id}/cancel/` | Cancel own appointment |
| POST | `/api/appointments/{id}/reschedule/` | Reschedule with slotId |
| GET / POST | `/api/doctor-portal/profile/` | Own profile / acceptance setting |
| GET / POST | `/api/doctor-portal/clinics/` | Own clinic list / create or update |
| GET / POST | `/api/doctor-portal/slots/` | Own schedule / publish a slot |
| POST | `/api/doctor-portal/close-slot/` | Block an unbooked slot |
| GET | `/api/doctor-portal/appointments/` | Own patient appointments |
| POST | `/api/doctor-portal/complete/` | Complete an eligible visit |

Sessions use HttpOnly cookies. Login/logout and appointment mutations require CSRF protection.

## Project structure

```text
backend/
  care/                     Models, serializers, ViewSets, permissions, admin, tests
    data/                   Chennai source snapshots and attribution
    management/commands/    Optional seed and metadata commands
    migrations/             Versioned schema and data migrations
  config/                   Django settings and URL configuration
  manage.py
  requirements.txt
  verify_http.py            Live HTTP integration check
frontend/
  app/                      Next.js routes and styles
  components/               Patient UI, clinic editor, area dropdown
  lib/                      API client, shared types, UI state
  package.json
  package-lock.json
```

## Checks and production build

```powershell
cd D:\slotcare\slotcare\backend
.\.venv\Scripts\python.exe manage.py test care
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
# Requires both local servers. Creates and removes only its temporary fixtures.
.\.venv\Scripts\python.exe verify_http.py
cd ..\frontend
npm test
npm run build
```

To serve a completed frontend production build locally, stop `npm run dev` and run `npm start`. Django must still be running.

Backend tests cover patient/doctor ownership, CSRF, filtering, availability, migration preservation, repeatable seeding, cancellation, rescheduling, and past-visit completion. Live HTTP checks exercise publishing, area search, booking, slot release, and completion through Next.js. Browser visual testing previously could not run because the browser access host was unavailable; a successful API check is not a visual UI check.

## Two-minute walkthrough

1. In a doctor browser window, sign in, select a clinic, publish tomorrow's slot, and enable acceptance.
2. In a separate patient/private window, select Chennai and the clinic's area, then filter by specialty. Check the next appointment and fee, select the new slot, and confirm.
3. Refresh and open My Appointments. Reschedule to another open time; show that the original time is available again. Cancel the replacement to release it.
4. Return to the doctor portal, block the released slot, and mark an eligible past visit completed. Select an area with no clinics to show Search all Chennai.

## Troubleshooting

- **npm cannot find package.json:** run npm inside `frontend/`, not `backend/`.
- **No module named django:** use `.\.venv\Scripts\python.exe` or activate that environment; system Python may be different.
- **Activation file not found:** check `.venv` versus `venv`, and `Scripts` versus `bin`. Direct executable commands do not require activation.
- **404 at port 8000 root:** open port 3000 for the website, or `/admin/` for Django Admin.
- **Doctor login rejected:** link the intended user to the Doctor profile, then sign out of another role before logging in.
- **No doctors/slots:** add clinics, set their neighbourhoods, publish future slots, and enable acceptance. Seeded slots become past over time; rerun the relevant seed or publish new slots.

## Local settings and Git

SQLite, DEBUG, HTTP cookies, and a development secret fallback are local-development defaults. Configure production secrets, HTTPS, and deployment settings before hosting. `DJANGO_SECRET_KEY` can be supplied as an environment variable. Environment files are ignored, but Django does not automatically load a `.env` file in this project.

The root `.gitignore` excludes both Python environment layouts, SQLite databases/backups, generated frontend output, dependencies, caches, logs, and local secrets. Keep Django migrations, directory source data, requirements, and package lockfiles versioned. Environment example templates may be committed; actual secrets must stay local. Ignore rules do not remove files already tracked by Git.
