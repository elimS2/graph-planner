## Settings Scheduler (Backups) — Roadmap

### Initial Prompt (translated)

Let’s add a new block in the Settings tab named "Schedule" (scheduler). Initially, it will configure the backup schedule; later, we can add other tasks. Create a separate roadmap file.

Analyse the Task and project — deeply analyze our task and the project and decide how to implement this best.

Create Roadmap — prepare a detailed, step-by-step plan in a separate document under docs/features. If the folder does not exist, create it. Document all discovered and tried issues, nuances, and solutions. During implementation, use this file as a todo checklist, update it, and record what was done, how it was done, problems encountered, and decisions taken. Do not delete items; only update their status and comment. If new subtasks appear, add them here. Remember that the project’s code, comments, and labels must be in English. After writing the plan, stop and ask me whether to start implementing it or adjust the plan.

Also include manual testing steps describing what to click in the UI.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

---

### Context & Constraints

- Current stack: Flask app with blueprints; heavy client-side logic in `app/templates/project.html`.
- We already implemented manual "Backup DB" with `POST /api/v1/settings/backup-db` and a service in `app/services/backups.py`.
- Configuration comes from `.env` via `app/utils/env_reader.py`; backup dir uses `BACKUPS_DIR`.
- No existing background scheduler in the codebase. We need a safe in-process scheduler (prefer APScheduler) with persistence strategy that fits SQLite and the app’s lifecycle.

Constraints and goals:
- Keep the solution simple and robust (KISS). Avoid long-running/shell processes.
- Ensure schedules survive server restarts (persistence) and aren’t duplicated (avoid double scheduling under multiple workers).
- Provide clear UI to configure backup cadence and a manual “Run now”.
- Future extensibility: add more scheduled tasks later (translations, cleanup).

### Design Overview

Backend
- Library: APScheduler (BackgroundScheduler) with job store (SQLite via SQLAlchemyJobStore) or minimal custom persistence in our DB.
- Single scheduler instance: created in app factory or an extension module, guarded to avoid duplicates (dev reloads, multiprocess). Optionally enable only in non-testing environments.
- Job: `scheduled_backup_job()` calls `perform_sqlite_backup()`; reuses `BACKUPS_DIR` and the same validation.
- API endpoints under `/api/v1/settings/scheduler/*`:
  - `GET /settings/scheduler` → returns current schedules and status
  - `POST /settings/scheduler/backup` → create/update backup schedule (cron/interval)
  - `DELETE /settings/scheduler/backup` → remove backup schedule
  - `POST /settings/scheduler/backup/run` → trigger backup immediately
  - Optional: `GET /settings/scheduler/jobs` → list jobs (for debugging)

Persistence options
1) APScheduler SQLAlchemyJobStore → simple, standardized; store in our existing SQLite file under a dedicated table.
2) Custom: store cron string in our own table and (re)apply on boot. Lean but more bespoke.

Choice: Start with APScheduler SQLAlchemyJobStore for reliability and less boilerplate; later we can switch if needed.

UI/UX
- Settings tab → new block "Schedule":
  - Controls:
    - Strategy select: "Disabled", "Daily", "Weekly", "Cron expression", "Every N hours".
    - If Cron: text field with validation and hint.
    - If Every N hours: numeric input for N, min 1.
    - Time-of-day picker for Daily/Weekly; weekday selector for Weekly.
    - “Run backup now” button.
  - Status area: shows last run time, last result (success/error), next run ETA.
  - Validation feedback inline; toasts for success/failure.
- Accessibility: labels, aria-*; consistent styles with existing Settings panels.

### Step-by-step Plan

1) Backend foundation [pending]
- Add dependency on APScheduler (version pinned in requirements.txt).
- Create `app/extensions.py` integration: `scheduler = BackgroundScheduler(...)` and `init_scheduler(app)`.
- Configure job store (SQLAlchemyJobStore) pointing to the same DB URI (or a separate file if needed).
- Ensure singleton behavior: init only once; avoid double-start on dev reload or multiple workers.

2) Backup job and helpers [pending]
- Implement `scheduled_backup_job()` in `app/services/backups.py` or a new `app/services/scheduler_jobs.py` that uses `perform_sqlite_backup()` and logs outcome.
- Add small wrapper to format job id: `"backup_db"`.

3) Scheduler API [pending]
- Blueprint: extend `settings_api` with routes:
  - GET scheduler status (current config, next run time, last run state).
  - POST set schedule: accepts mode (disabled/daily/weekly/cron/interval), time params; validates, creates/updates APScheduler job.
  - DELETE schedule: removes the job.
  - POST run-now: triggers `scheduled_backup_job()` immediately and returns result.
- Error handling: 400 for invalid config; 500 for unexpected.

4) Settings UI block [pending]
- Add new collapsible block `Schedule` in `#settingsPanel` of `project.html` with inputs described above.
- Wire interactions: load current state on open, submit changes to scheduler API, show toasts, and reflect status.
- Add minimal client-side validation (e.g., cron pattern presence; N>=1).

5) Persistence & startup [pending]
- On app startup, ensure scheduler is started and resumes jobs from job store.
- On config change via UI, jobs are added/updated/removed accordingly.

6) Manual testing [pending]
- With `.env` configured (`BACKUPS_DIR` set), set schedule to Daily at a near time or to Every 1 hour; verify next run and wait or temporarily trigger run-now.
- Verify backup files appear in the configured folder with distinct timestamps.
- Toggle Disabled, confirm jobs are removed and no further runs occur.
- Try invalid cron → expect validation error and no changes applied.

7) Rollback plan [pending]
- Feature flag the scheduler initialization (e.g., `SCHEDULER_ENABLED`), default on for dev/prod; off for testing if needed.
- To rollback UI: hide the Settings block with CSS; to rollback backend: don’t init scheduler, leave endpoints returning 404.

### Risks / Considerations
- Multiprocess servers can spawn multiple schedulers; ensure single-run using process-checks or deploy with a single worker (documented) or centralize scheduling.
- APScheduler with SQLite job store is fine for single-instance; for HA, consider external store (e.g., Postgres) and coalescing/misfire grace.
- Cron validation on the client is limited; validate on server as source of truth.
- Security: consider restricting scheduler endpoints to authenticated/authorized users when auth is enabled.

### Todos & Status Log
- [x] Add APScheduler dependency and integrate scheduler init
- [x] Implement scheduled backup job wrapper and logging
- [x] Create scheduler CRUD endpoints (status, set, delete, run-now)
- [x] Build Settings UI block with forms and validation
- [ ] Validate and persist schedule via API; reflect next run/last run in UI
- [x] Add tests for schedule persistence and run-now path (skipped by request; covered by manual tests)
- [x] Provide scripts/tests JSON tools to verify scheduler config and status
- [ ] Document decisions and update this roadmap through implementation


