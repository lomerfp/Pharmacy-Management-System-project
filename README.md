# Pharmacy Management System

A single-location pharmacy operations system for the academic project **Design and Development of a Relational Pharmacy Management System Database**. Academic context: Makerere University, College [...]

## Current status

This workspace is being implemented in SDLC phases. See [SDLC progress](SDLC_PROGRESS.md) for verified status and known gaps. Do not treat unfinished modules as production-ready.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS.
- `backend/`: Django, Django REST Framework, PostgreSQL.
- `docker-compose.yml`: local PostgreSQL service and application services.
- API validation, business rules, and database access belong in the backend. Browser storage is not the business database.

The 15 approved core entities are Role, Staff, Category, Drug, Batch, Supplier, PurchaseOrder, PurchaseOrderItem, Customer, Doctor, Prescription, PrescriptionItem, Sale, SaleItem, and Payment. Any[...]

## Development prerequisites

- Node.js 22 LTS or newer and npm.
- Python 3.12 or newer (the current workspace has Python 3.13.7).
- PostgreSQL 16+ or Docker Desktop with Compose v2.
- Git.
- VS Code extensions recommended: Python (Microsoft), Pylance (Microsoft), Docker (Microsoft), and ESLint (Microsoft). They are recommendations, not runtime dependencies.

## Quickstart (Docker Compose)

These steps will bring up a local development stack with a PostgreSQL database and both application containers.

1. Copy the example environment file and edit secrets if needed:

```bash
cp .env.example .env
# edit .env and replace any development-only passwords/secret values before sharing or deploying
```

2. Build and run the stack with Docker Compose:

```bash
docker compose up --build
```

3. The frontend will be available at `http://localhost:5173` and the API at `http://localhost:8000/api/`.

Notes:
- The `.env.example` is pre-configured to make the frontend container talk to the backend service by the service name (`VITE_API_BASE_URL=http://backend:8000/api`). When running the frontend locally outside Docker, update `VITE_API_BASE_URL` to `http://localhost:8000/api` or use the default in the example.
- If you need to run migrations or seed demo data manually:

```bash
# in a separate terminal (or inside the backend container)
cd backend
python manage.py migrate
python manage.py loaddata initial_data.json  # if present
python manage.py createsuperuser  # optional admin user
```

## Running locally without Docker

If you prefer to run the services directly on your machine:

1. Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# edit .env to point to your local Postgres if not using docker
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

2. Frontend

```bash
cd frontend
npm ci
# If backend is running locally use VITE_API_BASE_URL=http://localhost:8000/api
npm run dev
```

## Running tests

The project uses an automatic test DB selection so tests run against SQLite by default and do not require a running Postgres instance.

From the repository root:

```bash
# Python tests
python backend/manage.py test

# Frontend build (validates TypeScript/compile-time issues)
npm ci --prefix frontend
npm --prefix frontend run build
```

CI notes:
- The workflow is configured to run the backend tests (Django) and build the frontend. If you add or modify CI workflows, ensure the node build step sets VITE_API_BASE_URL appropriately when building the frontend.

## Troubleshooting

- If containers cannot start due to database authentication errors, confirm `.env` values for `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` match and that the `db` container is healthy.
- If the frontend fails to reach the API in Docker, open a shell in the frontend container and curl the backend service:

```bash
docker compose exec frontend sh -c 'curl -sS http://backend:8000/api/ | head -n 20'
```

- To run a simple smoke check against a running API locally, use the provided script `scripts/healthcheck.sh` (see below) or run:

```bash
curl -I http://localhost:8000/api/schema/
```

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
