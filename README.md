# IIT Ropar Facility Booking

An online replacement for IIT Ropar's paper facility booking workflow, built in four weekly increments
(see the LLD, Appendix A).

**Current state:** Week 1 (foundation and facility catalogue), now running on **PostgreSQL** instead of MongoDB,
following evaluator feedback after Week 1.

| Layer      | Stack                                                                 |
| ---------- | --------------------------------------------------------------------- |
| Frontend   | React 18 + TypeScript, Vite, React Router                             |
| Backend    | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic                       |
| Database   | PostgreSQL 14+ (psycopg 3 driver)                                     |
| Migrations | Alembic                                                               |

## What's built

- FastAPI backend with versioned REST API (`/api/v1`), env-based configuration, CORS, and a consistent
  error format (`{"error": {"code", "message", "details"}}`).
- `GET /api/v1/health` reports the API and database status (200 when PostgreSQL answers `SELECT 1`, 503 when it doesn't).
- `GET /api/v1/facilities?active=true` returns the catalogue with each facility's group, section, capacity,
  slot types, slot options and the tariff in effect today for all three rate categories.
- `GET /api/v1/facilities/{code}` returns one facility (404 in the standard error format if unknown).
- If PostgreSQL goes down while the app is running, endpoints return `503 DATABASE_UNAVAILABLE` instead of crashing.
- Alembic migration that creates the schema, with foreign keys and check constraints enforced by the database.
- An idempotent seed for 10 facilities, 11 facility slot types, 33 tariffs and 16 slot windows.
- A responsive catalogue page (group filters, tariff table per facility, loading/error/empty states, API status in the footer).
- Backend tests against a real PostgreSQL test database, and frontend component tests.

**Deferred (per the plan):** Google sign-in and draft requests (Week 2), submission/availability/approvals (Week 3),
costing, Estate, emails and admin (Week 4).

## Database schema

```text
facilities ─────────────┬──────────────< facility_slot_types (facility_id, slot_type)  PK
  id PK                 │                        ▲                 ▲
  code UNIQUE           │                        │ (facility_id,   │ (facility_id,
  facility_group CHECK  │                        │  unit)          │  slot_type)
  section CHECK         ├──────────────< tariffs ┘                 │
  capacity CHECK > 0    │                id PK, category CHECK,    │
  active                │                amount CHECK >= 0,        │
                        │                version, effective_from/to│
                        │                UNIQUE (facility_id, category, unit, version)
                        └──────────────< slot_windows ─────────────┘
                                         id PK, slot_key, start_time/end_time CHECK start < end
                                         UNIQUE (facility_id, slot_key)
```

Rules the **database** enforces (not just the Python code):

- Facility codes are unique; group, section, rate category and slot type must be one of the allowed values.
- A tariff or slot window must belong to an existing facility (foreign key).
- A tariff can only exist for a unit the facility supports. For example, a half-day tariff for classroom M5 is rejected,
  through the composite foreign key `(facility_id, unit) → facility_slot_types`.
- Amounts can't be negative; a tariff's `effective_to` must be after its `effective_from`; a slot's start is before its end.
- Deleting a facility deletes its slot-type rows (`ON DELETE CASCADE`).

The schema is defined in `backend/app/db/models.py` and created by the migration in `backend/alembic/versions/`.
A test (`test_migrations_match_models`) fails if the two ever disagree.

## Repository layout

```text
backend/
  alembic.ini               # Alembic config (URL comes from DATABASE_URL)
  alembic/versions/         # schema migrations (0001_master_data.py)
  app/
    main.py                 # app factory, routers, CORS
    core/config.py          # settings from environment / .env
    core/errors.py          # AppError + uniform error handlers (incl. 503 when the DB is down)
    db/models.py            # SQLAlchemy tables and constraints
    db/session.py           # engine, per-request session dependency, ping
    db/create_database.py   # creates the PostgreSQL database if missing
    db/seed_data.py         # facility, tariff and slot-window master data
    db/seed.py              # idempotent seed (python -m app.db.seed)
    repositories/           # SQL queries
    services/               # business logic (catalogue assembly, latest effective tariff)
    schemas/                # Pydantic response models
    api/                    # thin route handlers
  tests/
frontend/
  src/
    app/App.tsx             # routes and layout
    api/                    # fetch client + typed endpoint helpers
    components/             # header, API status, loading/error/empty states
    features/facilities/    # catalogue page, facility card, tests
docker-compose.yml          # optional PostgreSQL in Docker
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer (20+ recommended)
- PostgreSQL 14 or newer. On Windows, use the EDB installer from postgresql.org and remember the password you set
  for the `postgres` user. Or run `docker compose up -d postgres`.

## Setup and run

### 1. Backend

```bash
cd backend
pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `backend/.env` and replace both `YOUR_PASSWORD`s with your PostgreSQL password. If the password contains
`@ : / % #`, URL-encode it (for example `@` becomes `%40`).

```bash
python -m app.db.create_database   # creates the facility_booking database if missing
alembic upgrade head               # creates the tables
python -m app.db.seed              # loads master data; safe to run any number of times
uvicorn app.main:app --reload --port 8000
```

Check it:

- http://localhost:8000/api/v1/health
- http://localhost:8000/api/v1/facilities
- http://localhost:8000/docs (interactive API docs)

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

Open http://localhost:5173.

## Tests and checks

```bash
# Backend: needs PostgreSQL running. Uses a separate database, facility_booking_test,
# which is created, migrated and wiped automatically. Your real data is never touched.
cd backend
pytest -v
ruff check .

# Frontend
cd frontend
npm test
npm run typecheck
npm run build
```

## Configuration

All configuration comes from environment variables or a git-ignored `.env` file (see `backend/.env.example`).

| Variable                    | Default                                                          | Purpose                          |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------- |
| `APP_ENV`                   | `development`                                                    | Shown in `/health`               |
| `DATABASE_URL`              | `postgresql+psycopg://postgres:postgres@localhost:5432/facility_booking` | App database             |
| `TEST_DATABASE_URL`         | `...@localhost:5432/facility_booking_test`                       | Test database (name must end in `_test`) |
| `DATABASE_CONNECT_TIMEOUT`  | `5`                                                              | Seconds before the DB counts as down |
| `FRONTEND_URL`              | `http://localhost:5173`                                          | Allowed CORS origin(s), comma-separated |
| `VITE_API_BASE_URL` (frontend) | `http://localhost:8000/api/v1`                                | API base URL used by the browser |

## Seed data

`python -m app.db.seed` loads `backend/app/db/seed_data.py` with `INSERT ... ON CONFLICT DO NOTHING` on each row's
natural key (facility `code`; `facility_id + slot_type`; `facility_id + category + unit + version`;
`facility_id + slot_key`). Rerunning it never duplicates rows and never overwrites values changed in the database
later. It prints how many rows were inserted and how many were already present.

## Demonstration script

1. **Create the schema from nothing.** In pgAdmin, delete the `facility_booking` database if it exists. Then run
   `python -m app.db.create_database` and `alembic upgrade head`. In pgAdmin, refresh to show the four tables and their
   constraints (Schemas → public → Tables → tariffs → Constraints).
2. **Seed twice.** The first run reports `inserted=10 / 11 / 33 / 16`. The second reports `inserted=0`.
3. **Start the backend and check health.** http://localhost:8000/api/v1/health → `"database":"ok"`. Stop the
   PostgreSQL service (`services.msc` → postgresql-x64-NN → Stop) and reload: `503`, `"unreachable"`. Start it again.
4. **Start the frontend** and show the catalogue and its filters.
5. **Show the data comes from PostgreSQL.** In pgAdmin's Query Tool:
   `UPDATE tariffs SET amount = 16000 WHERE category = 'PRIVATE' AND amount = 15000 AND facility_id = (SELECT id FROM facilities WHERE code = 'M5');`
   Refresh the page to see the new price. Rerun the seed to show it does **not** overwrite the change.
6. **Show the database enforcing rules.** Try a half-day tariff for M5:
   `INSERT INTO tariffs (facility_id, category, unit, amount, display_label, version, effective_from) VALUES ((SELECT id FROM facilities WHERE code='M5'), 'PRIVATE', 'HALF_DAY', 100, 'x', 'demo', now());`
   PostgreSQL rejects it with `fk_tariffs_facility_unit`.
7. **Run the tests.** `pytest -v` and `npm test`.

## Assumptions and design notes

1. **Database changed from MongoDB to PostgreSQL** after Week 1 evaluation. The LLD's collections map to tables:
   `facilities`, `tariffs`, `slot_windows`, plus `facility_slot_types`, because a facility can support more than one
   booking unit and a SQL column can't hold a list. The API responses are unchanged, so the frontend didn't change.
2. **PostgreSQL specifically** was chosen because Week 3 needs overlapping bookings to be impossible. PostgreSQL can
   enforce that in the database with an exclusion constraint over a time range.
3. **Auditorium foyer** is shown as full day; the presentation gives a tariff but no slot duration.
4. **Slot times are placeholders.** Auditorium halves are 09:00–13:00 and 14:00–18:00. Sports 3-hour windows are
   09:00–12:00, 12:00–15:00 and 15:00–18:00. Full-day and per-day slots have no times.
5. **Tariff versions:** the seeded version (`2026-presentation-v1`) is effective from 1 Jan 2026. The catalogue shows,
   per facility/category/unit, the newest active tariff whose effective window includes now.
6. **Amounts are whole rupees** (integer). Computed costs (GST, cleaning) will use decimals in Week 4.
7. **No official data has been invented.** There is no payment URL, staff email or terms text yet.

## Known limitations

- No authentication yet; the catalogue is public and read-only.
- No admin editing of master data yet. Change values in pgAdmin or edit `seed_data.py` and reseed an empty database.
- The seed doesn't update rows that already exist (by design).
