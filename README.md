# Smart Student Bus Tracker

A smart school transportation management system connecting **Parents, Drivers, Students, and Administrators**.

## Current Status

Phase 3 — Core database and domain

* React + Vite frontend
* Flask backend
* Flask-CORS
* Frontend ↔ backend connection
* Backend health API
* Environment-backed configuration
* Role-protected administrative endpoints
* Reproducible backend dependency list
* Additive SQLite core-domain migration
* Parent, driver, admin, trip, and manual attendance APIs

## Project Structure

```text
smart-student-bus-tracker/
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── .venv/
│   └── app.py
│
├── .gitignore
└── README.md
```

## Requirements

* Python 3.11+
* Node.js 20+
* npm

## Configuration

Copy `.env.example` to `.env` at the project root and replace
`JWT_SECRET_KEY` with a long random value. Production requires this value;
development generates a temporary key when it is omitted.

## Run the Backend

Open a terminal:

```powershell
cd backend
.venv\Scripts\python.exe app.py
```

Backend:

```text
http://127.0.0.1:5000
```

Development seed identities can be created idempotently with:

```powershell
cd backend
.venv\Scripts\python.exe seed.py
```

The seed command creates development identities only and never creates face
encodings.

Health check:

```text
http://127.0.0.1:5000/health
```

## Run the Frontend

Open another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Vite will display the local URL in the terminal.

Example:

```text
http://localhost:5174/
```

## Phase 1 API

### GET `/api/health`

Returns:

```json
{
  "status": "ok",
  "message": "Smart Student Bus Tracker backend is running"
}
```

## Future Modules

The project will be developed incrementally:

1. Authentication
2. Admin management
3. Student management
4. Bus and route management
5. Face registration
6. Face recognition
7. Pickup/drop attendance
8. Driver dashboard
9. GPS tracking
10. Parent dashboard
11. Notifications
12. Bus timing
13. Alternative bus assignment
14. Excel reports
15. Events and feedback
16. Testing
17. Final UI refinement
18. Full system integration
