# Pharmacy Management System

A single-location pharmacy operations system for the academic project **Design and Development of a Relational Pharmacy Management System Database**. Academic context: Makerere University, College of Computing and Information Sciences, Department of Computer Science, Bachelor of Science in Computer Science, Database Management Systems / Database Systems Design, Lomer Francis Peter, Supervisor/Lecturer Mr. Lule Emmanuel, academic year 2026/2027.

## Current status

This workspace is being implemented in SDLC phases. See [SDLC progress](SDLC_PROGRESS.md) for verified status and known gaps. Do not treat unfinished modules as production-ready.

## Architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS.
- `backend/`: Django, Django REST Framework, PostgreSQL.
- `docker-compose.yml`: local PostgreSQL service and application services.
- API validation, business rules, and database access belong in the backend. Browser storage is not the business database.

The 15 approved core entities are Role, Staff, Category, Drug, Batch, Supplier, PurchaseOrder, PurchaseOrderItem, Customer, Doctor, Prescription, PrescriptionItem, Sale, SaleItem, and Payment. Any audit, stock-movement, or goods-receipt tables are documented implementation extensions. Batch uses physical `BatchID` and `UNIQUE(DrugID, BatchNumber)`; its approved conceptual identifying key is `(DrugID, BatchNumber)`. A supplier per batch is an explicit approved-version assumption; a future provenance extension is needed when identical manufacturer batch numbers arrive from multiple suppliers.

## Development prerequisites

- Node.js 22 LTS or newer and npm.
- Python 3.12 or newer (the current workspace has Python 3.13.7).
- PostgreSQL 16+ or Docker Desktop with Compose v2.
- Git.
- VS Code extensions recommended: Python (Microsoft), Pylance (Microsoft), Docker (Microsoft), and ESLint (Microsoft). They are recommendations, not runtime dependencies.

## Local setup (Windows PowerShell)

The commands below are the intended workflow; they will be updated as the runnable services are completed.

```powershell
Copy-Item .env.example .env
# Edit .env and replace every development-only password/secret before deployment.
docker compose up --build
```

Open the frontend at `http://localhost:5173`; the API is intended at `http://localhost:8000/api/`. If Docker is unavailable, install PostgreSQL locally, create an empty development database and least-privilege application user, then use the backend and frontend manual setup guides when available.

## Safety notes

- Do not use demo credentials or development secrets outside local development.
- Do not point migrations or seed scripts at production data.
- Completed sales and payments are immutable in ordinary application workflows.
- Non-cash payment references are manually recorded, not provider-verified.
- This academic system is not legal or regulatory certification.

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
