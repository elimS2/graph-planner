## Feature: Settings Page displaying .env contents

### Initial Prompt (translated to English)

Add a settings page that displays the contents of the env file.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in the file as thoroughly as possible all identified and tried issues, nuances, and solutions, if any. As you progress with the implementation of this task, you will use this file as a todo checklist, you will update this file and document in it what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If in the course of implementation it becomes clear that something needs to be added from the tasks - add it to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Also include steps for manual testing in the plan, i.e. what needs to be clicked in the interface.

==================================================

### Goals
- Provide a simple, secure settings page that shows the project’s `.env` key-value pairs.
- Ensure the page is discoverable from existing navigation and styled consistently with the app (Tailwind, minimal JS).
- Follow SOLID, DRY, KISS, Separation of Concerns, Clean Code; respect UI/UX principles: simplicity, consistency, accessibility, responsive design.

### Non-Goals
- Editing and persisting `.env` via UI (out of scope for this iteration).
- Exposing secrets in production environments without safeguards.

### Current Project Analysis
- Framework: Flask with an application factory `app.create_app`. Blueprints: `main`, `graph`, `tasks`, `tracking`, `users`.
- Templating: Jinja templates in `app/templates` with Tailwind and some AlpineJS/vanilla JS.
- Environment handling:
  - `app/__init__.py` uses `dotenv.load_dotenv()` to load `.env` into `os.environ`.
  - There are helper functions to read a `.env` file as raw key-value pairs (without exporting to env):
    - `scripts/start_flask_server.py: load_dotenv_values(root: Path) -> Dict[str, str]`.
    - `wsgi.py: _load_dotenv_values(root: Path) -> dict`.
  - This duplication suggests we should centralize a reusable reader.
- Navigation: `index.html` header has links to Health and Auth buttons. No Settings link yet.

### Design Decisions
1. Add a reusable `.env` reader utility
   - New module: `app/utils/env_reader.py`
   - Function: `read_dotenv_values(root: Path) -> Dict[str, str]`
   - Behavior: parse `.env` at project root; ignore comments/blank lines; split on first `=` only; trim whitespace; return dict.
   - This consolidates logic used by `scripts/start_flask_server.py` and `wsgi.py` for consistency and DRY.

2. Settings route and template
   - Route: `GET /settings` in the existing `main` blueprint (`app/blueprints/main/routes.py`).
   - Controller will:
     - Determine project root (parent of current file’s parent) and call `read_dotenv_values`.
     - Optionally load `os.environ` as a fallback if `.env` is missing (flag `env_missing=True`).
     - Mask sensitive values by default (e.g., keys containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PWD`, `AUTH`, `BEARER`): show first 2 and last 2 characters, mask the rest.
     - Pass to template a list of entries with `key`, `value`, `masked_value`, and `is_sensitive`.
   - Template: `app/templates/settings.html`
     - A responsive table of variables with columns: Key, Value (masked by default with toggle per-row), Source (`.env` or `os.environ` fallback), Copy button.
     - Client-side filter box (by key substring) using a tiny inline JS.
     - Non-editable, read-only.
     - Accessibility: proper labels, focus styles, button semantics.

3. Security & availability
   - The page is intended for development/testing only by default.
   - Gate access: allow only when `app.config['ENV'] in {"development", "testing"}` or `app.debug` is True. In production, return 404 by default.
   - Optionally also require an authenticated user in future iterations (out of scope now).

4. Navigation
   - Add a small link to `/settings` in `index.html` and `project.html` headers next to existing links.

5. Error handling & logging
   - If `.env` not found, show an informational banner on the page and fall back to `os.environ` list (filtered to relevant keys: `HOST`, `PORT`, `DATABASE_URL`, etc., plus any starting with app-specific prefixes like `GT_` if applicable). Keep the UI resilient.

### Data Structures
- Python: `List[Dict[str, Any]]` for entries passed to the template.
- Jinja: loop to render rows; JS to toggle masking per row; no framework dependency.

### UI/UX Outline
- Minimalistic page: title "Settings", subtitle "Environment Variables".
- Search input to filter keys in real-time.
- Table: monospace for Key and Value; masked values with • characters; eye icon button to toggle; copy button; badge for sensitive values.
- Info alerts for `.env` missing or parse issues.
- Responsive: table scrolls horizontally on small screens.

### Risks & Mitigations
- Risk: Secrets exposure in production.
  - Mitigation: environment gating (dev/test only); masking by default; per-row reveal.
- Risk: Large environment causing slow render.
  - Mitigation: simple DOM, no heavy JS; client-side filter; lazy no-op for very large values (truncate display to ~4k chars with option to expand).
- Risk: Multiple `.env` formats (export statements, quotes).
  - Mitigation: Basic parser recognizes `KEY=VALUE`, trims; ignore complex cases; document limitations.

### Acceptance Criteria
- Visiting `/settings` in development displays parsed `.env` variables as a table.
- Sensitive variables are masked by default; can be toggled per-row.
- If `.env` is absent, page renders, indicating fallback to `os.environ` (limited set), without server errors.
- Page is not available in production (404).
- Navigation link to Settings is visible in headers.

### Manual Testing Steps (UI)
1. Start the Flask app (development mode).
2. Open `/` and click the "Settings" link in the header.
3. Verify the page title and the table of variables.
4. Use the search input to filter keys (e.g., type `HOST`).
5. Click the eye icon on a non-sensitive key to reveal/hide value.
6. Click the eye icon on a sensitive key and confirm masking toggles correctly.
7. Click the "Copy" button and paste to confirm the value is copied (masked state should not affect clipboard; copy the real value).
8. Temporarily rename `.env` to simulate missing file and reload page; verify fallback banner and values (from `os.environ`).
9. Switch to a production-like config and confirm `/settings` is not accessible (404).

### Implementation Plan (Checklist)
- [x] Create `app/utils/env_reader.py` with `read_dotenv_values(root: Path) -> Dict[str, str]`.
- [x] Add `GET /settings` in `app/blueprints/main/routes.py` gated to dev/test; integrates masking and fallback.
- [x] Add template `app/templates/settings.html` with responsive table, toggle, copy, filter.
- [x] Add Settings entry: link in `index.html` header; sidebar tab in `project.html`.
- [x] Add small unit/integration checks (API test script).
- [x] Document limitations in this file (quotes, multi-line values).

### Step 1 Notes
- Implemented `app/utils/env_reader.py` with safe `.env` parsing, `is_sensitive_key`, and `mask_value` helpers.
- Reasoning: centralize logic to avoid duplication in `scripts/start_flask_server.py` and `wsgi.py` and ensure DRY.
- No lint issues detected.

### Step 2 Notes
- Implemented `/settings` route in `main` blueprint.
- Dev/test gating: allowed when `current_app.debug` is True or env is one of `development`, `testing`, `test`; otherwise returns 404.
- Reads `.env` via `read_dotenv_values(root)`; if empty, falls back to a conservative subset of `os.environ` (`FLASK_ENV`, `APP_ENV`, `HOST`, `PORT`, `DATABASE_URL`, `LOG_LEVEL`).
- Prepares entries with `is_sensitive_key` and masked values via `mask_value`.
- No lint issues detected.

### Step 3 Notes
- Created `app/templates/settings.html`:
  - Responsive table with Key, Value, Actions.
  - Default masked display, per-row Show/Hide toggle.
  - Copy button copies the real value (not masked) to clipboard.
  - Filter input to quickly narrow keys.
  - Fallback banner shown when `.env` missing (as provided by controller context).
- No lint issues detected.

### Open Questions
- Should we support editing `.env` values from the UI in a future iteration?
- What key patterns should be considered sensitive beyond the defaults? Provide a list?
- Should the page require authentication even in development?

### Future Enhancements (Not in current scope)
- Download `.env` as a file from the UI (with confirmation and dev-only gating).
- Inline edit with audit log and server-side write-back (requires file locking and safety checks).
- Group variables by prefix and add quick filters.

### New Requirement: Slide-out Settings Panel (in-app panel)
User requested that settings be available as a slide-out panel similar to the existing Task Panel, with possible tabs or toggle buttons between panels.

Proposed approach:
- Add a new slide-out panel component that can render different content panes: "Task", "Settings" (and future ones).
- For the Project page (`project.html`):
  - Add a "Settings" button near the existing "Toggle Sidebar" that opens the same right-hand panel but switches the content to the Settings view.
  - Settings pane shows the same env table UI (re-used via server-rendered HTML fragment or client-rendered via a JSON API). Given minimal JS stack, we can:
    - Option A (fastest): fetch `/settings` as HTML and inject the central `<section>` into the panel body.
    - Option B (cleaner API): expose `/api/v1/settings/env` returning JSON of env entries, render with small client JS template.
- For the Index page (`index.html`): optionally reuse the same panel pattern later.

Security & Visibility:
- Maintain the same dev/test gating on the data endpoint or during fetch; if unavailable, show a notice.

Checklist (Panel work):
- [ ] Introduce a small panel manager with tabs/toggles (Task | Settings) in `project.html`.
- [x] Add a lightweight client fetch to retrieve env entries (prefer JSON endpoint `/api/v1/settings/env`).
- [x] Render a compact table inside the panel with mask/show/copy.
- [x] Keep responsive behavior and keyboard accessibility; remember last active tab.
 - [x] Document and test gating behavior.

### Step 4 Notes (API for panel)
- Added `app/blueprints/settings/routes.py` with `GET /api/v1/settings/env`.
- Registered the blueprint in `app/__init__.py`.
- Same gating as the page route; returns entries with masked/real values and meta source.
- No lint issues detected.

### Step 5 Notes (Slide-out panel in project.html)
- Added tabs (Task | Settings) in the sidebar; persisted last active tab in localStorage.
- Implemented fetch from `/api/v1/settings/env`, render masked values with Show/Hide and Copy.
- Added filter input, source label, and fallback alert.
- No lint issues detected.

### Navigation Links
- Added a "Settings" link in `index.html` header.
  - Note: In `project.html`, Settings is available as a tab in the sidebar rather than a header link (by design).

### Step 6 Notes (Gating and API test script)
- Strengthened gating to also honor `TESTING=True` for both page and API.
- Added test script `scripts/tests/test_settings_env_api.py`:
  - Boots app with testing config.
  - Calls `/api/v1/settings/env` and writes a summary to `scripts/tests/json-result.json`.
### Notes on SOLID/DRY/KISS & SoC
- Single Responsibility: `env_reader` parses files; route composes data; template renders UI.
- DRY: centralize `.env` parsing; reuse across scripts if needed.
- KISS: read-only view, minimal JS, no heavy client frameworks.
- Separation of Concerns: utility vs. view vs. template clearly separated.

### Known Constraints & Nuances
- `.env` parser is intentionally simple; quoted values and escaped `=` beyond the first are not fully supported; we will document and potentially extend if needed.
- Very long values will be truncated visually but still copy the full value.

### Current Status
- Planning complete. Awaiting approval to proceed with implementation.


