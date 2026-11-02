# Smart Student Bus Tracker

A React + Vite frontend and Flask backend for school-bus tracking, face-recognition attendance, parent updates, and fleet administration.

## Project layout

- `frontend/` — React user interface (Parent, Driver, Admin)
- `backend/` — Flask API, SQLite database setup, face recognition, GPS, trips, and notifications
- `.env.example` — root-level environment variable template

## 1. Backend setup (Windows PowerShell)

From the project root:

```powershell
Copy-Item .env.example .env
py -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
```

Open `.env` and replace `JWT_SECRET_KEY` with a long, random secret. Keep `DATABASE_PATH=backend/smart_student_bus_tracker.db` for this project layout. The backend initializes/upgrades its SQLite schema when it starts. For a brand-new local development database only, create the local starter accounts with:

```powershell
cd backend
..\backend\.venv\Scripts\python.exe seed.py
cd ..
```

The development seed uses `admin / Admin@123`, `driver1 / Driver@123`, and `parent1 / Parent@123`. These are **local-demo credentials only**. Do not use them in a deployed or public environment. The seed does not overwrite an existing username's password.

Start the API:

```powershell
cd backend
..\backend\.venv\Scripts\python.exe app.py
```

The API listens at `http://127.0.0.1:5000`. Face recognition requires the InsightFace and ONNX Runtime packages in `backend/requirements.txt`; the first model load may take longer than later requests.

## 2. Frontend setup

Open a second PowerShell window from the project root:

```powershell
cd frontend
Copy-Item ..\.env.example .env.local
npm.cmd ci
npm.cmd run dev
```

The Vite development server uses port `5174` by default. `VITE_API_BASE_URL` should point to `http://127.0.0.1:5000` for local development. Browser camera and location permissions must be allowed; use `localhost` or HTTPS for browser GPS/camera access.

For a production frontend build:

```powershell
npm.cmd run build
```

## 3. Required Admin setup sequence

1. Sign in as Admin.
2. Create a Driver account in **Drivers**.
3. Create a Bus in **Buses**.
4. Open **Routes & Stops** and create a route with a unique route code; add its stops with valid coordinates and pickup/drop schedules.
5. In **Buses**, assign both a Driver and a Route to the Bus. A Driver should have one active bus assignment.
6. In **Students**, create each student and the linked Parent account. Assign the student to the correct Bus using the **Assigned Bus** selector.
7. Register the student's face from the student row.

A Parent can then sign in and view only their linked child's assigned bus, change today's status between `COMING` and `NOT_COMING`, and view pickup/drop notifications. A Driver can sign in, choose a `PICKUP` or `DROP` trip, start it, allow GPS and camera access, and record attendance through face recognition. Admin can monitor every active bus under **Live Bus Tracking**.

## 4. Important behavior

- New/no-record Parent travel status defaults to `COMING`.
- A `NOT_COMING` student is blocked from face-attendance marking for that local school date.
- Face recognition is restricted to students assigned to the logged-in Driver's active Bus.
- Pickup/drop notifications are created for the Parent accounts linked to a student after attendance is recorded.
- Parent bus location access is checked server-side against the Parent–student–bus relationship.
- Driver trip creation and GPS uploads are restricted to that Driver's active assignment.

## 5. Render deployment settings

For the existing Render frontend/backend pair, set the frontend Static Site environment variable `VITE_API_BASE_URL` to `https://smart-student-bus-tracker-backend.onrender.com` before building. Set the backend `CORS_ORIGINS` to include `https://smart-student-bus-tracker.onrender.com` (and any local development origins you still use). Rebuild/redeploy the frontend after changing `VITE_API_BASE_URL`, because Vite embeds it into the build. Keep the backend `JWT_SECRET_KEY` private. In production, configure all required `BOOTSTRAP_*` account values before starting the backend with `APP_ENV=production`.

Use real test accounts and test student faces only in a controlled environment. Do not commit `.env`, database files, or face-image uploads.
