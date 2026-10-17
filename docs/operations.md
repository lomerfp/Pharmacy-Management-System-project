# Setup, Deployment, Backup, and Restoration

## Local setup: Windows PowerShell

Prerequisites: Node.js 22.12+ (Vite 8 requirement), Python 3.13 recommended, Git, and either Docker Desktop Compose v2 or MySQL 8.4/InnoDB. Docker is the simplest path. A Python venv and dependencies are local, not committed.

```powershell
Copy-Item .env.example .env
# Edit .env. The supplied passwords and Django key are development placeholders.
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
npm --prefix frontend ci
```

Start MySQL and application services when Docker Desktop is installed:

```powershell
docker compose up --build
```

The Compose backend runs migrations on startup against the Compose MySQL service. This is a local development configuration using Django's development server and Vite's development server; it is not a production deployment. Stop services with `Ctrl+C`, then `docker compose down`; that preserves the named MySQL volume. `docker compose down -v` deletes the local database volume and is destructive; do not run it unless you intentionally want to erase development data.

Manual local database alternative: install MySQL 8 with InnoDB and create a least-privilege local development user. For the installed Windows service, connect using the interactive password prompt:

```powershell
& 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe' --protocol=tcp --host localhost --port 3306 --user root --password
```

At the MySQL prompt, create only the new development schema and app account. Replace the password placeholder before executing; never put the real password in a shell argument or repository:

```sql
CREATE DATABASE pharmacy_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'pharmacy_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_NEW_LOCAL_SECRET';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON pharmacy_dev.* TO 'pharmacy_app'@'localhost';
```

Set those app credentials in `.env`, using `MYSQL_HOST=127.0.0.1`. Do not run the statements against production or an existing database. From the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings"
python backend\manage.py migrate
python backend\manage.py runserver 127.0.0.1:8000
```

For an existing legacy pharmacy database with `staff(StaffID, RoleID, FullName, Email, IsActive)` and `role(RoleID, RoleName)`, set `PHARMACY_LEGACY_SCHEMA=true` in `.env` instead of using the fresh-install schema. In this mode Django maps Staff and Role as read-only tables and uses `staff_credentials` plus password-reset tokens as app-owned tables. Back up the database first, then run `python backend\manage.py migrate`; the legacy migration path does not create, alter, or copy passwords into `staff` or `role`. Existing accounts have no password in those tables, so enroll one through `python backend\manage.py set_staff_credential staff@example.com`; the command prompts for the password without echoing it. Staff signup, staff edits, role edits, and demo seeding are disabled in legacy mode. The rest of the inventory and sales API still needs table-by-table legacy mapping before it can be used against this schema.

In another PowerShell window:

```powershell
npm --prefix frontend run dev
```

Open `http://localhost:5173`; API documentation is at `http://localhost:8000/api/docs/`. Users can submit a staff access request from the login screen. Requests cannot log in until an admin assigns a role and activates the account under Staff & Access. To create fictional local records, set `DEMO_STAFF_PASSWORD` in the current PowerShell process to a development-only password of at least 12 characters, keep `DJANGO_DEBUG=true`, then run `python backend\manage.py seed_demo`. The command refuses when DEBUG is false. It creates six named accounts that share that password; rotate/deactivate them before shared use. Remaining frontend modules are not complete.

## VS Code

Open the current workspace folder. Recommended extensions are listed in `.vscode/extensions.json`. Run **Pharmacy: Frontend dev server**, **Pharmacy: Django development server**, or **Pharmacy: Run unit tests (SQLite only)** from Terminal > Run Task. Use the `Django: Pharmacy API` launch configuration for breakpoints. Create `.venv` and `.env` first. API currently authenticates with JWT; no demo staff credentials have been seeded.

## Production prerequisites (not configured/deployed)

Use a production WSGI/ASGI server behind TLS and a reverse proxy; set a long random secret outside source control; disable DEBUG; set allowed hosts and trusted origins; use secure cookies; provision a restricted MySQL role and private network; build/serve static assets; configure monitored logs and alerts; rotate secrets; review migrations; define retention and access policy; and test recovery. Never use the bundled Django or Vite development servers as internet-facing production servers. No application deployment or live database migration was performed.

## Backup and restoration runbook (procedure, not yet rehearsed)

For a local Compose database, a backup can be written with PowerShell redirection:

```powershell
docker compose exec -T db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$MYSQL_DATABASE"' > .\backup.sql
```

Keep backups encrypted and access-controlled; do not commit them. To verify restore without touching the source, create a separate disposable database, then restore into that target only:

```powershell
docker compose exec -T db mysql -uroot -pYOUR_LOCAL_ROOT_PASSWORD -e "CREATE DATABASE pharmacy_restore_test"
Get-Content .\backup.sql | docker compose exec -T db mysql -uroot -pYOUR_LOCAL_ROOT_PASSWORD pharmacy_restore_test
```

Verify tables/migrations and reconcile sample counts in the restored target. Delete the disposable target only after confirming it is not production or the source database. This procedure has not been executed. For real operations, schedule off-host encrypted backups, monitor failures, define RPO/RTO, and rehearse restore regularly. Never include a database password in a shell argument or repository file.
