# Test Results

Updated 2026-10-01. Results describe actual executed checks, not planned checks.

## Passed

- `frontend`: `npm run build` passed after login/reset, dashboard, inventory, POS, and report screens; TypeScript and Vite production bundle completed (1,571 transformed modules).
- `backend`: `manage.py check` passed with no issues.
- `manage.py test pharmacy.tests --settings=config.test_settings -v 1`: 21 tests passed on the in-memory SQLite test database. Coverage includes role permissions, limited cashier customer lookup, batch uniqueness, FEFO/anonymous OTC/rollback/idempotency, prescription authorization and review, password reset/logout, dashboard reconciliation, partial/duplicate/over receipts, report permissions/CSV, audit permissions, reasoned stock adjustments, and guarded repeatable demo data.
- `manage.py makemigrations pharmacy` generated `pharmacy/migrations/0001_initial.py` for all 15 core entities and the documented extension models.
- `manage.py spectacular --file ../docs/openapi.yaml --validate --settings=config.test_settings` generated and validated `docs/openapi.yaml` with zero reported schema errors after endpoint annotations were added.

## Not run / limitations

- MySQL80 is running and port 3306 is reachable, but workspace credentials are absent and a no-password root login was denied. Applying migrations, MySQL constraints, InnoDB concurrency/locking, backup, and restore remain unverified. Docker is unavailable. See `docs/operations.md` for local schema/app-user setup without putting a password on a command line.
- SQLite ignores `select_for_update`; the passing SQLite tests do not establish concurrency safety.
- No browser end-to-end interaction was run. Purchasing, prescriptions, staff, settings, and audit UI remains incomplete.

## Commands used

From `frontend` in the configured Windows `cmd` terminal:

```cmd
npm run build
..\.venv\Scripts\python.exe ..\backend\manage.py check
..\.venv\Scripts\python.exe ..\backend\manage.py makemigrations pharmacy
..\.venv\Scripts\python.exe ..\backend\manage.py test pharmacy.tests --settings=config.test_settings -v 1
```

The SQLite test-settings module is intentionally separate; normal Django settings remain MySQL.
