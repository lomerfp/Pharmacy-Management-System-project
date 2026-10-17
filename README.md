# Pharmacy Management System

A single-location pharmacy operations system for the academic project **Design and Development of a Relational Pharmacy Management System Database**. Academic context: Makerere University, College [...]

## Current status

This workspace is being implemented in SDLC phases. See [SDLC progress](SDLC_PROGRESS.md) for verified status and known gaps. Do not treat unfinished modules as production-ready.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS.
- `backend/`: Django, Django REST Framework, MySQL.
- `docker-compose.yml`: optional local MySQL service for containerized development.
- API validation, business rules, and database access belong in the backend. Browser storage is not the business database.

The 15 approved core entities are Role, Staff, Category, Drug, Batch, Supplier, PurchaseOrder, PurchaseOrderItem, Customer, Doctor, Prescription, PrescriptionItem, Sale, SaleItem, and Payment. Any[...]

## Development prerequisites

- Node.js 22 LTS or newer and npm.
- Python 3.12 or newer (the current workspace has Python 3.13.7).
- MySQL 8.x or Docker Desktop with Compose v2.
- Git.
- VS Code extensions recommended: Python (Microsoft), Pylance (Microsoft), Docker (Microsoft), and ESLint (Microsoft). They are recommendations, not runtime dependencies.

## Local MySQL setup

This project is configured to use the existing MySQL schema in the local `.env` file. Copy the sample file and fill in the credentials for your local instance:

```bash
cp .env.example .env
# edit .env and set DB_NAME=pharmacy_management_db, DB_USER, DB_PASSWORD, DB_HOST=127.0.0.1, DB_PORT=3306
```

Do not commit `.env` to Git. Keep the connection settings local to your machine.

## Quickstart (Docker Compose)

These steps will bring up a local MySQL service and the web app containers when desired.

```bash
docker compose up --build
```

The frontend will be available at `http://localhost:5173` and the API at `http://localhost:8000/api/`.

Notes:
- The app expects the existing MySQL database at `127.0.0.1:3306` for direct local development.
- If you run the stack in Docker, the `db` service should resolve to the same database name and credentials in `.env`.
- Do not run destructive migrations against the existing production or academic database until you have reviewed the exact schema impact.

## Running locally without Docker

If you prefer to run the services directly on your machine:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# edit .env to point to your MySQL server and database name
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Frontend:

```bash
cd frontend
npm ci
# If backend is running locally use VITE_API_BASE_URL=http://localhost:8000/api
npm run dev
```

## Running tests

The project expects a dedicated MySQL test database when used for database-compatibility validation. If you need a disposable SQLite-only override, set `USE_SQLITE_TESTS=true` explicitly; otherwise the default path is the configured MySQL connection.

From the repository root:

```bash
# Python tests against the configured MySQL database
python backend/manage.py test

# Frontend build (validates TypeScript/compile-time issues)
npm ci --prefix frontend
npm --prefix frontend run build
```

## Troubleshooting

- If the app cannot connect to MySQL, confirm `.env` has the exact values for `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`.
- If you are using Docker, make sure the `db` container is healthy and the app is using the same database name and credentials.
- The project currently has no shipped SQL schema files or legacy MySQL table definitions in the repository, so the exact field-to-model mapping must be compared against the live schema before destructive changes are made.

## Documentation map

- [SDLC progress and feasibility](SDLC_PROGRESS.md)
- [Software Requirements Specification](docs/srs.md)
- [Database design, ERDs, and DFDs](docs/database-design.md)
- [Requirements traceability and UAT](docs/requirements-traceability.md)
- [Current API surface](docs/api.md)
- [Generated OpenAPI schema](docs/openapi.yaml)
- [SQL report examples and indexes](docs/sql-reports.md)
- [Test evidence and limitations](docs/test-results.md)
- [Setup, deployment, backup, restore](docs/operations.md)
- [Role-oriented user guide](docs/user-guide.md)
- [Academic report and presentation outline](docs/academic-report-outline.md)
- [Known issues and future work](docs/known-issues.md)
