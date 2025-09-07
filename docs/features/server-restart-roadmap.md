## Server Restart Button in Settings — Roadmap

### Initial Prompt

Add a "Restart Server" button to the Settings tab in the sidebar, where the env file is displayed. Review how our server is restarted using the existing start/stop scripts; reuse what makes sense. I want a button that, when pressed, can restart the server.

Analyze the task and the project deeply and decide how best to implement it.

Create a detailed, step-by-step implementation plan in a separate document file. We have a `docs/features` folder for this. If it doesn’t exist, create it. Document all discovered and tried issues, nuances, and solutions in this file. As the implementation progresses, use this file as a TODO checklist, update it and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and add comments. If, in the course of implementation, it becomes clear that something needs to be added, add it to this document. This will help maintain context and ensure we don’t forget planned tasks. Remember that only English is allowed in code, comments, and project labels. After writing the plan, stop and ask me if I agree to start implementing it or if anything needs adjusting.

Also include manual testing steps (what to click in the UI).


### Current State — Analysis

- **Settings UI**: `GET /settings` renders `app/templates/settings.html`, which shows `.env` values with masking, copy, and filter.
- **Settings API**: `GET /api/v1/settings/env` in `app/blueprints/settings/routes.py` returns environment key/values. Both pages are gated to dev/test mode.
- **Health endpoint**: `GET /api/v1/health` exists in `app/blueprints/graph/routes.py` and returns `{ status: ok, pid }`.
- **Start server**: `scripts/start_flask_server.py` loads `.env`, configures logging under `instance/logs` (or `LOGS_DIR`) and runs Flask dev server with `debug=False`, `use_reloader=False`, `threaded=True`.
- **Stop server (script)**: `scripts/tests/stop_server.py`:
  - Reads `pid` from `/api/v1/health` when possible.
  - On Windows uses `taskkill /F /T` to kill the process tree by PID.
  - Has fallback by listing processes listening on the configured port and killing them.
  - Saves JSON to `scripts/tests/json-result.json` per local test conventions.
- **Constraints**:
  - We run a dev server directly via Flask, not a process manager. There’s no external supervisor that brings the app back after kill.
  - Windows: using `taskkill /T` from a child process can kill the entire tree including the relauncher if it’s spawned by the server itself.
  - We must not use inline Python in the terminal; test scripts write JSON to `scripts/tests/json-result.json`.


### Design Decision

- Implement a safe, self-service restart in dev/test by combining:
  1) A new endpoint `POST /api/v1/settings/restart` (dev/test only) that:
     - Spawns a detached relauncher script.
     - Immediately triggers a graceful shutdown of the current Flask server using Werkzeug shutdown hook (no `taskkill`).
     - Returns 202 JSON so the UI can show feedback.
  2) A new script `scripts/restart_server.py` that:
     - Waits until the current server is down (health failing or port closed).
     - Then starts `scripts/start_flask_server.py` in a new process.
     - Uses Windows-safe `creationflags` (DETACHED) and POSIX `start_new_session=True` to avoid being killed with the parent.
  3) UI changes to `settings.html`:
     - Add a prominent "Restart Server" button with confirmation.
     - After click, call the restart API, then poll `/api/v1/health` every 1s. When it’s back, show success and auto-refresh.

- Rationale:
  - Avoid `stop_server.py`’s Windows `taskkill /T` from inside the server process (it could terminate our relauncher child).
  - Graceful shutdown via Werkzeug lets the server finish the current response, then exit, without nuking children.
  - The relauncher handles the timing to bind the port only after it’s free.


### Security and Environment Gates

- The restart endpoint and the Settings page remain available only in development/testing environments, consistent with existing gating logic.
- No credentials required in dev; in future, could add a simple CSRF token or local-only restriction if needed.


### Implementation Plan (Step-by-step)

1) API: Add restart endpoint
   - File: `app/blueprints/settings/routes.py`.
   - Route: `POST /api/v1/settings/restart`.
   - Behavior:
     - Gate to dev/test (reuse existing gating function/logic used in env endpoint).
     - Compute project root and python executable path (`sys.executable`).
     - Spawn `scripts/restart_server.py` detached with args derived from `.env` (`HOST`, `PORT`).
     - Trigger Werkzeug server shutdown via `request.environ["werkzeug.server.shutdown"]()`.
     - Return 202 JSON `{ "data": { "restarting": true } }`.

2) Script: Create `scripts/restart_server.py`
   - Parse `.env` (reusing minimal loader like in start script) to get `HOST` and `PORT`.
   - Poll health or port until server is down.
   - Launch `python scripts/start_flask_server.py` detached.
   - Optional: Wait up to N seconds for health to become OK, then exit.
   - Windows: use `creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP|CREATE_NO_WINDOW`.
   - POSIX: use `start_new_session=True` and close stdio.

3) UI: Add button and client logic to `app/templates/settings.html`
   - Add a primary button "Restart Server" in the header section next to the filter.
   - On click:
     - Show confirm dialog.
     - `fetch('/api/v1/settings/restart', { method: 'POST' })`.
     - Show a status banner: "Restarting...".
     - Start polling `/api/v1/health` every 1s; on success, show "Restarted" and reload the page.
     - Handle errors and timeouts with visible feedback.

4) Logging & UX polish
   - Ensure `scripts/start_flask_server.py` continues writing logs under `LOGS_DIR`.
   - In UI, link to `/api/v1/health` and show PID before/after if available.

5) Docs & Tests
   - Keep this roadmap updated as work progresses.
   - Add a minimal test script under `scripts/tests/` if we need to verify the restart flow in isolation, saving JSON to `scripts/tests/json-result.json` (only if run via terminal).


### Edge Cases and Mitigations

- The user clicks restart multiple times: debounced in UI; backend quickly returns 202, shutdown occurs once.
- Port in use by another process: relauncher retries a few times and logs failure; UI times out and shows guidance.
- Not in dev/test: endpoint returns 404 (maintain safety).


### Manual Test Checklist

1) Preconditions
   - `.env` contains `HOST` and `PORT` (defaults are fine: 127.0.0.1:5050).
   - Server started via `scripts/start_flask_server.py`.

2) UI flow
   - Open `/settings`.
   - Verify environment variables are shown; note current PID via `/api/v1/health` link in header.
   - Click "Restart Server".
   - Confirm the dialog.
   - Observe a banner "Restarting..." and a spinner.
   - After ~3–10 seconds, the page detects server is back (health OK, PID changed) and reloads.
   - Verify the PID changed.

3) Failure path
   - Temporarily bind the port with another process; click restart.
   - Confirm UI shows error after timeout and provides instructions to check logs.


### Alternatives Considered

- Calling `scripts/tests/stop_server.py` from the server, then launching start script: rejected due to Windows `taskkill /T` potentially terminating the relauncher spawned by the same process tree.
- Using an external supervisor (e.g., `watchdog`, `nssm`, `pm2`-like) to auto-restart: heavier setup, out of scope for a dev-only button.


### Rollout Plan

- Implement behind dev/test gate only; no prod impact.
- Keep changes localized to settings blueprint, template, and a new script.


### Future Enhancements

- Add a lightweight auth or local-only restriction to restart endpoint.
- Add a small status widget showing current health and PID in the Settings page header.


### Status Log

- [Done] Implement API endpoint `POST /api/v1/settings/restart` (dev/test gated) in `app/blueprints/settings/routes.py`.
- [Done] Add `scripts/restart_server.py` relauncher (detached spawn; waits for port free; starts `scripts/start_flask_server.py`; writes JSON result to `scripts/tests/json-result.json`).
- [Done] Update `settings.html` with a "Restart Server" button and client logic (confirm, call API, poll `/api/v1/health`, UX banners, auto-reload).
- [Pending] Manual test on Windows 10 in local dev.

### Notes from implementation

- We avoided using `scripts/tests/stop_server.py` from inside the server because on Windows it relies on `taskkill /T`, which could kill the relauncher spawned from the same process tree. Instead, the API uses Werkzeug shutdown, and the relauncher handles restart lifecycle.
- Restart API returns 202 immediately and schedules shutdown on a short delay to ensure the HTTP response flushes.
- UI provides clear feedback and a timeout fallback after 30 seconds with guidance to check logs.

### 2025-08-31 — Iteration updates

Implemented reliability/UX improvements and status reporting:

- API and server shutdown
  - Capture `werkzeug.server.shutdown` within request and call it from a background thread, then fallback to `os._exit(0)` if needed to guarantee port release.
  - Use `pythonw.exe` on Windows to avoid console windows; for POSIX use `start_new_session=True` and redirect stdio.
  - Extracted cross-platform spawn helper `app/utils/process.py::spawn_detached_silent` to remove per-call platform branches.

- Relauncher enhancements (`scripts/restart_server.py`)
  - Records `pid_before` and `pid_after`, writes detailed phases.
  - If port is still in use, performs a soft kill fallback by PID (Windows: `taskkill /T`, POSIX: `SIGTERM`→`SIGKILL`).
  - Waits for health to come back and checks PID change; distinguishes `restarted` vs `pid_unchanged` vs `started_but_unhealthy`.
  - Accepts `--op-id` and writes results to `instance/restart_ops/<op_id>.json` in addition to `scripts/tests/json-result.json`.

- Status API and UI
  - New `GET /api/v1/settings/restart/status/<op_id>` returns relauncher JSON; used by UI to show precise status (including PID before/after).
  - Buttons on `/settings` and project Settings tab now: fetch `op_id`, wait for DOWN, poll status/health for UP with PID change, then reload.

- Current issue observed
  - On some runs PID did not change because the original process did not terminate quickly; status file indicated `port_still_in_use`.
  - Applied fixes: captured shutdown func correctly, added small delay before exit, added `os._exit(0)` fallback, added kill-by-PID in relauncher before starting.

### Plan — next steps to reach green test (PID change)

1) Validate end-to-end via test script `scripts/tests/restart_via_api.py` — DONE (PID changed, status `restarted`).
2) UI polish — DONE: toast shows `PID before→after` after a successful restart.
3) Document op_id artifacts — DONE: `instance/restart_ops/<op_id>.json` records `pid_before`/`pid_after`/`status`.
4) Optional: expose `pid_before`/`pid_after` in UI Server Info after reload (future enhancement if needed).

### Manual Test Checklist (updated)

1) Open Settings tab and note current PID in Server Info.
2) Click "Restart Server"; confirm dialog.
3) Observe status banners; restart should succeed within ~30–45s.
4) After reload, verify PID changed in Server Info.
5) Inspect `instance/restart_ops/<most_recent>.json` and ensure it contains `status: restarted`, `pid_before != pid_after`.



