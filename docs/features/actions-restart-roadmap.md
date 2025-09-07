## Actions Tab — Server Restart Button & Header Toggle — Roadmap

### Initial Prompt (translated)

We have a restart button in the sidebar on the Settings tab within the System Info block. I want to display this button also on the Actions tab, with a checkbox to show or hide the button in the header. Implement it the same way as other buttons on this tab.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions to implement this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document all identified and tried issues, nuances, and solutions as you progress. During implementation you will use this file as a todo checklist; update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and comment. If it becomes clear during implementation that something needs to be added, add it to this document. This will help us keep the context window, remember what we have already done and not forget to do what was planned. Remember that only English language is allowed in code and comments. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context & Current State (Analysis)

- The restart feature is already implemented and wired in two places:
  - Standalone Settings page (`app/templates/settings.html`) with buttons `#btnRestartTop` and `#btnRestart` and a JS handler `doRestart()`.
  - Project sidebar Settings panel (`app/templates/project.html`), under “Server Info” block, with inline button `#btnRestartInline` and a self-contained wiring IIFE that calls `POST /api/v1/settings/restart` and polls health and status via `GET /api/v1/health` and `GET /api/v1/settings/restart/status/<op_id>`.
- There is an Actions tab (`#tabActions`) in `project.html`. It mirrors header actions and provides a pattern for per-action checkboxes “Show in header” driven by `localStorage` keys `actions.header.show.<id>`. This is set up in the IIFE `wireActionsPanel()` around lines ~3220–3308.
- Existing ACTIONS registry includes many header buttons (Add Node, Add Edge, Critical Path, Fit, Reset View, Group, Ungroup, Collapse, Expand, Screenshot, Backup DB, Export JSON, Import JSON). Each action has:
  - `headerId`: header toolbar button id
  - `panelId`: matching button inside Actions panel
  - `storageKey`: localStorage key for header visibility
  - `defaultShow`: default visibility state in header
- The header currently does not include a restart button. The Settings panel has its own restart button wiring and HTML.
- Backend endpoints already exist: `POST /api/v1/settings/restart`, `GET /api/v1/settings/restart/status/<op_id>`, and `GET /api/v1/health`.

Implication: To add restart into Actions panel with a header visibility checkbox like others, we should (1) add a header button for Restart (hidden by default), (2) add corresponding panel button in Actions with the checkbox wired via the existing ACTIONS registry pattern, and (3) reuse the existing restart JS flow (either by extracting a shared handler or delegating the panel/header to click the existing Settings restart function).

### Design Overview

- UI additions:
  1) Header toolbar: add a `#btnRestartHeader` button (label: "Restart"). Hidden by default, controlled by `localStorage('actions.header.show.btnRestartHeader')`.
  2) Actions tab: add a button `#btnRestartHeaderPanel` placed among other actions in the Actions panel. A “Show in header” checkbox will be auto-wired by extending the ACTIONS registry.
  3) Settings panel: keep existing inline restart button `#btnRestartInline` unchanged.

- JS behavior:
  - Create a shared `async function doRestart()` in the main script of `project.html` or reuse the existing restart logic snippet by extracting it to a function. Prefer reusing the already robust logic from Settings panel in `project.html` (IIFE wireRestart) by refactoring into a named function `doRestart()` placed near other helpers.
  - Wire both header `#btnRestartHeader` and panel `#btnRestartHeaderPanel` to call `doRestart()`.
  - Extend `ACTIONS` array in `wireActionsPanel()` with an entry for Restart: `{ headerId: 'btnRestartHeader', panelId: 'btnRestartHeaderPanel', storageKey: 'actions.header.show.btnRestartHeader', defaultShow: false }`.
  - Let existing checkbox wiring automatically add the “Show in header” checkbox next to the panel button.

- Accessibility & UX:
  - Add `aria-label` and `title` to buttons, keep consistent size and colors with other critical actions (e.g., rose/red for Restart to signify danger).
  - Confirmation dialog before calling restart; visible toast/banners as already implemented.
  - Respect the current success flow: poll for DOWN then UP; display PID change hint when available.

### Step-by-step Plan

1) Extract shared restart handler in `project.html` [pending]
   - Introduce `async function doRestart()` modeled on the existing Settings-wired IIFE.
   - Ensure it logs via the existing `restartLog()` helper and uses banners/toasts.

2) Add header button [pending]
   - In the main toolbar of `project.html`, add a hidden-by-default button with id `btnRestartHeader` and label "Restart".
   - Style similar to critical actions: `bg-rose-600 text-white`; include `title` and `aria-label`.

3) Add Actions panel button [pending]
   - In the Actions tab markup, add a mirror button with id `btnRestartHeaderPanel` (same label and semantics) placed with other action buttons.

4) Extend ACTIONS registry [pending]
   - In `wireActionsPanel()` extend the `ACTIONS` array with the restart entry.
   - This will auto-wire the checkbox and header visibility persistence.

5) Wire click handlers [pending]
   - Add listeners for both `#btnRestartHeader` and `#btnRestartHeaderPanel` to call `doRestart()`.
   - Keep the existing `#btnRestartInline` wiring intact.

6) Manual polish [pending]
   - Ensure the button is hidden by default in header (`defaultShow: false`).
   - Ensure reset-to-defaults respects hidden default.
   - Ensure Actions panel renders the “Show in header” checkbox for Restart.

7) Docs & Tests [pending]
   - Update this roadmap statuses.
   - Add manual test steps (below). No terminal-based automated test is needed for UI toggle; backend restart is already covered by existing scripts/UI flows.

### Edge Cases & Considerations

- Double-click restarts: prevent by disabling the button during in-flight operation; current `doRestart()` flow shows banners and can set a simple guard (optional).
- Visibility logic is localStorage-based; defaults should not expose Restart in header unless explicitly turned on.
- Ensure that adding the new header button does not shift layout undesirably; keep responsive wrapping consistent.

### Manual Test Checklist

1) Preconditions
   - App running in dev/test mode.

2) Actions tab UI
   - Open project page and switch to the Actions tab.
   - Verify a new "Restart" action button is present with a checkbox “Show in header”.
   - Toggle the checkbox on: the header gains a visible "Restart" button.
   - Toggle the checkbox off: the header hides the "Restart" button.
   - Click the Actions tab "Restart" button: confirm dialog appears; proceed to restart; page reloads after success.

3) Header button
   - With checkbox on, click the header "Restart" button; confirm; ensure restart completes and page reloads.

4) Reset to defaults
   - Click "Reset visibility" in Actions (if available); confirm that header "Restart" is hidden again and the panel checkbox is unchecked.

5) Server Info consistency
   - After a restart triggered from either place, check that the Server Info block in Settings shows updated PID and last restart info as before.

### Todos & Status Log

- [x] Extract shared `doRestart()` in `project.html` (reusing existing Settings logic)
  - Implemented via lightweight delegation: header/panel buttons trigger the existing inline Settings restart wiring (`#btnRestartInline`) when present, with a direct API fallback. Full refactor into a named shared function is optional and can be done later without changing behavior.
- [x] Add header button `#btnRestartHeader` (hidden by default)
- [x] Add panel button `#btnRestartHeaderPanel` in Actions
- [x] Extend `ACTIONS` with Restart entry and wire checkbox
- [x] Wire click handlers for both buttons (delegating to restart flow)
- [ ] Manual test across flows and document results here

### Rollback Plan

- Remove the restart entry from the ACTIONS registry and the buttons from header/actions panel. Existing Settings restart remains unaffected.


