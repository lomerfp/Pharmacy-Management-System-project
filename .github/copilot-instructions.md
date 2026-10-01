# Project checklist

- [x] Verify that the copilot-instructions.md file in the .github directory is created.
- [x] Clarify the project requirements and confirm the stack: Django backend, React frontend, and SQLite test configuration.
- [x] Scaffold the project and confirm the workspace structure is in place.
- [x] Customize the project with the pharmacy models, API foundation, and service layer implementation.
- [x] Install the recommended VS Code extensions and keep the recommendation list in .vscode/extensions.json.
- [x] Compile the project: the frontend build succeeds, and the Django SQLite test suite passes.
- [x] Create and run the project tasks for frontend build and unit-test verification.
- [ ] Launch the full application stack when a PostgreSQL or Docker-backed environment is available for local runtime validation.
- [x] Ensure the documentation is present and the project status notes remain current.

## Verified status

- Frontend build: passed with `npm --prefix frontend run build`.
- Backend validation: passed with the task `Pharmacy: Run unit tests (SQLite only)`.
- Launch readiness: the app is ready for runtime checks in a local PostgreSQL-backed environment, but full launch is intentionally deferred until Docker/PostgreSQL is available.

## Working conventions

- Keep communication concise and focused.
- Use the existing task definitions in .vscode/tasks.json for common build and validation commands.
- Prefer SQLite-only validation for automated backend checks unless a full PostgreSQL-backed environment is available.
- Do not claim full production readiness for modules that are still environment-dependent or intentionally incomplete.
