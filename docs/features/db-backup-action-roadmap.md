## Database Backup Action — Roadmap

### Initial Prompt (translated)

In the sidebar we have an Actions tab with buttons and checkboxes to show/hide the corresponding buttons in the header.

Add a new button that is hidden in the header by default. This button will create a backup of the database into a backups folder, which is specified in the project's root .env file.

If the .env file is missing, or the constant is missing, or it is empty, then show a message telling the user to provide the specific constant in the .env file.

Analyze the task and the project deeply and decide how to implement it best.

Create a detailed, step-by-step plan in a separate document under docs/features. If such a folder does not exist, create it. Document all identified and tried issues, nuances and solutions; during implementation, use this file as a todo checklist, update it, and record what was done, how it was done, any problems encountered, and decisions taken. Do not delete items; only update their status and comment. If new subtasks emerge, add them here to preserve context.

Also include steps for manual testing, i.e., what needs to be clicked in the UI.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

After writing the plan, stop and ask for confirmation before implementing or to adjust the plan if needed.

---

### Context & Current State

- The app uses Flask with blueprints; UI is primarily in `app/templates/project.html` with extensive client-side logic.
- The Actions tab already exists in the sidebar with a registry-based approach to mirror header buttons, including per-action "Show in header" checkboxes persisted in `localStorage` (e.g., keys like `actions.header.show.btnFit`).
- There are Settings endpoints under `/api/v1/settings/*` in `app/blueprints/settings/routes.py`. These endpoints already parse `.env` using `app/utils/env_reader.py` and implement dev/test gating for sensitive ops (e.g., restart).
- Database configuration is set in `app/config.py`. By default, SQLite database resides under `instance/graph_tracker.db` or project root fallback, unless `DATABASE_URL` is provided.

Implication: We can add a new backend endpoint in the Settings blueprint (or a new dedicated Ops/Backups blueprint) to perform a database backup. The frontend action will live in the Actions tab registry and optionally in the header (default hidden).

### Goals & Non-Goals

- Goal: Add a single-click "Backup DB" action in the Actions tab that triggers a server-side backup of the database into a configured backups directory.
- Goal: Add a corresponding header button that is hidden by default and controlled by the Actions tab checkbox.
- Goal: Provide clear user feedback for success and failure. If `.env` is missing or the backup directory constant is missing/empty, show a helpful instruction message.
- Non-goal: Implement cross-database backups for all engines. Initial scope focuses on SQLite (primary current deployment). For non-SQLite engines, return a meaningful error response and document future work.

### Configuration

- New `.env` constant: `BACKUPS_DIR` (absolute or relative to project root). Examples:
  - `BACKUPS_DIR=backups` (relative to project root)
  - `BACKUPS_DIR=C:/data/graph-tracker/backups` (Windows absolute path)

Validation rules:
- `.env` file must be readable (we already have a safe reader).
- `BACKUPS_DIR` must be present and non-empty.
- The directory must exist or be creatable by the app user; otherwise, return an error with guidance.

### Backend Design

- Module: `app/services/backups.py`
  - Function: `perform_sqlite_backup(backups_dir: Path, db_uri: str) -> dict`
    - Resolve the actual SQLite file path from `db_uri` (must start with `sqlite:///`).
    - Verify source DB file exists.
    - Ensure `backups_dir` exists (create with `parents=True, exist_ok=True`).
    - Create a filename like `graph_tracker_YYYYmmdd_HHMMSS.sqlite` (or include a short random suffix for uniqueness) and copy the DB file atomically if possible.
    - Return `{ ok: true, path: str, size_bytes: int, created_at: iso }` on success.
    - Return structured errors on failure with clear `message` and optional `hint`.

- Endpoint: `POST /api/v1/settings/backup-db`
  - Location: `app/blueprints/settings/routes.py` (same blueprint `settings_api`).
  - Auth/Gating: Unlike restart, backups should be allowed beyond dev/test. If login is enabled in your environment, prefer `@login_required` and role checks in the future. For now, no dev-only gate.
  - Behavior:
    1) Resolve project root and read `.env` via `read_dotenv_values(root)`.
    2) Validate `BACKUPS_DIR`; if missing/empty → `400` with message "Provide BACKUPS_DIR in .env at project root".
    3) Determine current DB URI (`current_app.config['SQLALCHEMY_DATABASE_URI']`).
    4) If not SQLite, return `400` with message that only SQLite is supported in v1.
    5) Call `perform_sqlite_backup` and return JSON.

Error handling & messages:
- 400: `.env` missing or `BACKUPS_DIR` missing/empty → include a clear instruction on how to set it.
- 400: DB engine unsupported → "Only SQLite is supported in this version."
- 500: I/O or unexpected errors → include `message` and `detail` (in DEBUG only) and log server-side.

### Frontend Design

- Actions registry: Add a new action row in `project.html` under the Actions panel.
  - Header button ID: `btnBackupDB` (new)
  - Panel button ID: `btnBackupDBPanel` (new)
  - Storage key: `actions.header.show.btnBackupDB`
  - Default header visibility: `false`

- Wiring:
  - Create a shared handler `performBackupDb()` that: `await fetch('/api/v1/settings/backup-db', { method: 'POST' })`.
  - On success: show a toast/banner with the saved file path (trimmed for readability) and offer a link to open folder if feasible (non-blocking enhancement; for now, text-only).
  - On error 400: show a warning message instructing to set `BACKUPS_DIR` in `.env` at the project root.
  - On error 500: show a generic failure message; encourage checking server logs.
  - Bind both `#btnBackupDBPanel` and `#btnBackupDB` to call `performBackupDb()`.

- Header visibility checkbox:
  - Add a checkbox row to the Actions panel for `Backup DB` with caption "Show in header".
  - Persist state using existing helpers and apply to `#btnBackupDB` visibility. Default: hidden.

### File Naming & Retention

- Filename: `graph_tracker_YYYYmmdd_HHMMSS.sqlite`.
- Optional (future): add short hash or suffix to avoid collisions when multiple backups happen within the same second.
- Optional (future): retention policy (e.g., keep last N backups) — not in initial scope.

### Security & Safety

- Verify the resolved backup directory is within allowed paths if a policy exists; otherwise, document that `BACKUPS_DIR` is user-controlled and should be trusted by the operator.
- Do not expose full filesystem internals to unauthenticated users. When auth is enabled, protect the endpoint.
- Ensure the response does not leak secrets; only return the backup path and size.

### Cross-Platform Considerations

- Use `pathlib.Path` for path resolution and creation.
- Handle Windows paths correctly (drive letters, backslashes) — returning forward-slash paths in JSON is acceptable for display.
- Avoid shelling out; perform copy via Python file I/O.

### Manual Test Plan

1) Prepare `.env` with `BACKUPS_DIR=backups` at the project root; ensure the folder is writable.
2) Start the server and open a project page.
3) Go to the Actions tab.
4) Verify a new row "Backup DB" is visible with a panel button and a "Show in header" checkbox (unchecked by default).
5) Click "Backup DB" in the Actions tab:
   - Expect a success message with the created file path.
   - Check that the file appears under the configured backups directory.
6) Toggle "Show in header" ON → confirm the header now displays the "Backup DB" button; click it and observe identical behavior.
7) Reload the page → verify the header visibility preference persists; toggle OFF and confirm it disappears again.
8) Temporarily remove or blank `BACKUPS_DIR` in `.env` and restart the server:
   - Click "Backup DB" → expect a warning message instructing to set `BACKUPS_DIR` in `.env`.
9) If using a non-SQLite `DATABASE_URL`:
   - Click "Backup DB" → expect a clear error stating that only SQLite is supported in this version.

### Future Enhancements (Out of Scope for v1)

- Add support for backing up non-SQLite databases (e.g., PostgreSQL via pg_dump) with secure credentials handling.
- Add retention policy and automatic pruning.
- Add UI to browse and download backup files.
- Add success notification with a quick link to the backup folder (platform-specific).
- Add background job support for long-running backup operations.

### Todos & Status Log

- [x] Backend: create `app/services/backups.py` with `perform_sqlite_backup`.
- [x] Backend: add `POST /api/v1/settings/backup-db` endpoint with validation and structured errors.
- [x] Frontend: add `Backup DB` to Actions registry and wire handler; default header hidden.
- [x] Frontend: add user feedback toasts/banners for success/failure/missing env.
- [ ] Docs: update this file with implementation notes and decisions as we proceed.
- [x] Tests: add unit tests for backup service and integration tests for the endpoint.
- [x] Scripts: add `scripts/tests/` JSON-output script to exercise env handling as per workspace rules.

### Design Decisions (initial)

- Use `.env` constant name `BACKUPS_DIR` to keep naming concise and clear.
- Scope to SQLite initially; fail fast for other engines with clear messaging.
- Place endpoint under Settings blueprint for operational affinity and existing `.env` tooling.


