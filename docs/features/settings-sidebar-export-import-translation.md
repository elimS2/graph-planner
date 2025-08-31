## Settings Sidebar: Export/Import JSON and Translation Block

Status: planned

### Initial Prompt (translated)

Add to the sidebar's Settings tab the following blocks and controls:

- Export-Import JSON: add buttons "Export JSON" and "Import JSON"; the block can be named exactly "Export-Import JSON".
- Translation: add buttons "Translation Stats" and "Run Translate", plus a language toggle and a checkbox "Show Hidden".

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement it.

=== Create Roadmap ===

Create a detailed step-by-step plan for implementing this task in a separate file-document. We have a folder `docs/features` for this. If there is no such folder, create it. Document in as much detail as possible any problems found and tried, nuances and solutions, if any. As you progress with the implementation of this task, you will use this file as a todo checklist, you will update this file and document what has been done, how it was done, what problems arose and what solutions were made. For history do not delete items, you can only update their status and comment. If during the implementation it becomes clear that something needs to be added to the tasks, add it to this document. This will help us keep the window of context, remember what we already did, and not forget to do what was planned. Remember that only the English language is allowed in code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Include this prompt I wrote to you in the plan itself, but translate it into English. You can call it something like "Initial Prompt" in the plan document. This is needed to preserve in our roadmap file the exact context of the task without a "broken telephone" effect.

Also include steps for manual testing in the plan, i.e., what to click in the interface.

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context and Current State (analysis)

- The project view template is `app/templates/project.html`. It already contains:
  - A top toolbar with buttons `Export JSON`, `Import JSON` (via hidden file input), `Screenshot`, `Help`, a language selector `#langSelect`, a checkbox `#showHiddenToggle`, and a button `#btnTrStats` for translation stats.
  - Working client-side handlers for export/import at the bottom of the template:
    - Export fetches `/api/v1/projects/{id}/nodes` and `/api/v1/projects/{id}/edges` and downloads a JSON blob.
    - Import reads a local JSON file and posts new nodes to `/api/v1/projects/{id}/nodes` (edges are not imported currently), then reloads the graph.
  - Settings sidebar (`#settingsPanel`) with collapsible blocks (e.g., LOD, Server Info, .env). A collapsible helper persists state in `localStorage`.
  - Language and Show Hidden affect data loading via request params: `lang` and `include_hidden` are appended to fetch URLs.

- Back-end endpoints relevant to translation live in `app/blueprints/graph/routes.py`:
  - `GET /api/v1/projects/<project_id>/translation/stats` returns missing/stale counts.
  - `POST /api/v1/projects/<project_id>/translate` performs synchronous translation for nodes/comments (with options), and
  - `POST /api/v1/projects/<project_id>/translate/async` enqueues an async background job via `services.async_jobs`.

- There is a `settings` API blueprint (`app/blueprints/settings/routes.py`) for environment info and dev restart, unrelated to export/import yet.

Implications:

- We can implement Settings sidebar blocks without changing the back-end: reuse existing client logic and existing translation endpoints.
- To avoid duplicated logic between top toolbar and Settings, we should extract small JS functions (export/import, translation actions, language/show-hidden syncing) and bind them to both sets of controls. IDs in Settings must be unique (no reuse of top toolbar IDs) with two-way sync where appropriate.

### UX/Interaction Design

- Settings tab receives two new blocks:
  1) Export-Import JSON
     - Button "Export JSON" (primary style)
     - Button or label+file input "Import JSON" (safe style). On import, append nodes; show a confirmation and basic error feedback. Keep behavior consistent with the top toolbar.
     - Non-destructive import: same as toolbar, append nodes only. Edges import remains out-of-scope (documented limitation).

  2) Translation
     - Dropdown "Language" mirroring `#langSelect` options.
     - Checkbox "Show Hidden" mirroring `#showHiddenToggle`.
     - Button "Translation Stats" triggers the same flow as `#btnTrStats` (fetch stats and display inline in the block or alert). Minimal implementation: modal-less inline text area / small panel.
     - Button "Run Translate" triggers `POST /translate/async` with the currently selected language and sensible defaults; show job id and a link to logs endpoint (optional: poll job status if simple enough).

- Synchronization:
  - Settings controls have distinct IDs (e.g., `#settingsLangSelect`, `#settingsShowHiddenToggle`, `#settingsBtnExportJSON`, `#settingsImportInput`, `#settingsBtnTrStats`, `#settingsBtnRunTranslate`).
  - Language and Show Hidden are mirrored to/from existing toolbar controls through event listeners; changes in one reflect in the other and trigger the same refresh/filters.
  - Persist the last selected Settings tab and collapsed states (already done for other blocks). Persist language and show hidden as today (keep existing keys).

- Accessibility:
  - Use `<label for>` associations, keyboard activation (Enter/Space) for toggles, focus styles consistent with the rest.

### Technical Design

Front-end (in `app/templates/project.html`):

- Markup: Add two new blocks under `#settingsPanel` after existing ones:
  - `#exportImportBlock` with the two buttons and hidden file input.
  - `#translationBlock` containing a select (same options as `#langSelect`), a checkbox, and two action buttons.

- JavaScript:
  - Extract reusable functions near existing handlers:
    - `async function exportProjectJSON(projectId)`
    - `async function importProjectJSONFromFile(file, projectId)`
    - `async function fetchTranslationStats(projectId, lang)`
    - `async function runTranslateAsync(projectId, lang, opts)`
  - Bind these to existing toolbar controls and the new Settings controls.
  - Implement two-way sync for language and show hidden:
    - When either control changes, update the other and call existing refresh routines (`fetchGraph`, list refresh) and persist in `localStorage`.
  - Provide minimal user feedback (disable buttons while running, show success/error messages). Reuse existing alert/toast style or simple `alert()` as a baseline.

Back-end:
  - No changes required for this scope.
  - Document current import limitation (nodes-only, no edges) and the existing translation endpoints.

Data/State:
  - Continue using URL params `lang` and `include_hidden` for data fetches.
  - Persist preferences in `localStorage` keys already used by the page (do not introduce conflicting keys).

### Step-by-Step Implementation Plan

1. Front-end scaffolding
   - Add `#exportImportBlock` and `#translationBlock` HTML to `#settingsPanel` with Tailwind utility classes consistent with other blocks.
   - Add Settings-specific control IDs.

2. JS refactor to reusable functions
   - Factor existing top-toolbar export/import logic into `exportProjectJSON` and `importProjectJSONFromFile`.
   - Add translation helpers (`fetchTranslationStats`, `runTranslateAsync`).

3. Wire Settings controls
   - Bind click/change handlers for the new buttons, select, and checkbox.
   - Implement sync with `#langSelect` and `#showHiddenToggle` (two-way).

4. UX feedback
   - Disable buttons during async operations; re-enable on completion or error.
   - Display stats inline within `#translationBlock` (small pre/code region) and a brief success message for Run Translate with job id.

5. Documentation and cleanup
   - Update this roadmap (statuses, notes, decisions).
   - Ensure English-only labels in UI.

### Manual Test Checklist

Prereq: Open a project page.

- Settings tab visibility
  - Click "Settings" tab; ensure new blocks are visible: "Export-Import JSON" and "Translation".

- Export JSON (from Settings)
  - Click "Export JSON"; a file `project-<id>.json` should download with `nodes` and `edges` arrays.

- Import JSON (from Settings)
  - Click "Import JSON" and choose a previously exported file with nodes.
  - Nodes are appended; the graph reloads; no errors in console; edges are not created (current limitation).

- Language toggle sync
  - Change language in the Settings dropdown; verify the top toolbar language reflects it and translated titles/comments render accordingly.
  - Change language in the top toolbar; Settings dropdown updates accordingly.

- Show Hidden sync
  - Toggle "Show Hidden" in Settings; verify nodes with `is_hidden` appear faint and data loads with `include_hidden=1`.
  - Toggle from the toolbar; Settings checkbox mirrors the state.

- Translation stats
  - Click "Translation Stats"; stats appear inline (counts) and match API `GET /translation/stats` for the selected language.

- Run translate (async)
  - Click "Run Translate"; confirm a job id is returned; optionally open logs for the job in a separate area/tab.

### Risks, Constraints, and Decisions

- Duplicate controls could desync: mitigated with two-way listeners and single-source of truth in memory and `localStorage`.
- Import currently supports nodes only; edges import is out-of-scope for now and explicitly documented.
- Translation jobs can be long-running; we will use async endpoint and minimal feedback to keep UI responsive. Advanced progress UI can be a follow-up.

### Out-of-Scope / Future Work

- Dedicated export/import backend endpoints (with edges import and id remapping).
- In-UI job progress panel with polling and cancellation.
- Validation and preview for import JSON; selective import.
- Granular translation options (include comments/stale/force) in UI.

### Acceptance Criteria

- Settings tab contains the two new blocks with fully working controls.
- Language and Show Hidden in Settings mirror and control the same state as toolbar controls.
- Export and Import in Settings produce the same results as the existing toolbar actions.
- Translation Stats and Run Translate operate against the current project and selected language.
- All UI labels are in English; no linter errors introduced.

### Work Log / Updates

- [done] Create roadmap document and await approval.
- [done] Added HTML blocks in Settings: Export-Import JSON and Translation (with language select, show hidden, stats and run buttons), IDs prefixed with `settings*`.
- [done] Refactored export/import to reusable functions and bound to Settings controls; file input resets after use.
- [done] Wired Translation Stats and Run Translate; added inline feedback (`settingsTrStats`, `settingsTrJob`) and basic button disable/labels during async.
- [todo] Manual test pass; update this file with results and any fixes.

### Update: Toolbar cleanup and collapsible Settings

- [done] Removed toolbar buttons for Export/Import JSON and Translation (Stats/Run) to avoid duplication.
- [done] Made new Settings blocks collapsible with toggles (`exportImportToggle`/`exportImportBody`, `translationToggle`/`translationBody`) and wired them via existing collapsible helper alongside Server Info and .env.
- [note] JS made resilient if toolbar elements are missing (wrapped listeners in try/catch), since actions now live in Settings.

### Update: Move language and show hidden to Settings only

- [done] Removed toolbar `langSelect` and `showHiddenToggle` controls.
- [done] Introduced helpers `getCurrentLang()` and `isShowHiddenEnabled()`; all fetch flows (graph, lists, previews) now reference these helpers.
- [done] Settings controls (`settingsLangSelect`, `settingsShowHiddenToggle`) persist state via `localStorage` and trigger graph reloads.

### Update: Visibility block

- [done] Moved "Show hidden" into its own collapsible block `Visibility` with ids `visibilityToggle`/`visibilityBody` and checkbox `settingsShowHiddenToggle`.
- [done] Added a short explanatory text inside the expanded `Visibility` block clarifying the visual treatment and effect on data loading.

### Update: Zoom (LOD) block

- [done] Renamed LOD block to "Zoom" and made it collapsible via `zoomToggle`/`zoomBody`.

### Polish

- [done] Button states: disable/aria-busy during async (Stats/Run Translate/Import), success/error toasts added.
- [done] Collapsible sections: uniform chevron; per-section collapsed state persisted via localStorage.
- [done] Preferences: language and show hidden persist and initialize Settings controls.
- [done] Accessibility: added aria-label/title to export/import and translation buttons; toasts use aria-live.


