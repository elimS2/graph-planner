## Move Export/Import JSON from Settings to Actions — Roadmap

### Initial Prompt (translated to English)

In the sidebar, we currently have Export/Import JSON in Settings. Move these buttons to Actions; it seems more logical to place them there since this is not a setting but an action.

=== Analyse the Task and project ===

Deeply analyze our task and project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in as much detail as possible all discovered and tried issues, nuances, and solutions, if any. As you progress in implementing this task, you will use this file as a todo checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in code and comments, and in project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing — i.e., what needs to be clicked in the UI.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow the UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context and Current State (analysis)

- The project view is rendered by `app/templates/project.html`.
- In Settings tab, there is a block `#exportImportBlock` with controls:
  - `#settingsBtnExportJSON` — Export JSON button
  - `#settingsImportInput` — hidden `<input type="file">` for Import JSON
- JS helpers already exist and are shared:
  - `exportProjectJSON(projectId)` — fetches nodes/edges and downloads a JSON file
  - `importProjectJSONFromFile(file)` — parses JSON and appends nodes; edges import is not handled in Settings copy, header generic wiring handles it consistently via the helper
- There are two wiring sections related to Export/Import:
  - Generic wiring (intended for header toolbar) looks for `#btnExportJSON` and `#importInput` and attaches listeners if elements exist.
  - Settings-specific wiring looks for `#settingsBtnExportJSON` and `#settingsImportInput` and attaches listeners plus success toasts.
- The Actions tab (`#actionsPanel`) already contains `#actionsMainBlock`, a single consolidated panel for actions with visibility management mirroring header buttons.
- Ordering keys exist for panel block persistence:
  - `DEFAULT_SETTINGS_IDS` includes `exportImportBlock`. Removing the block requires adjusting defaults and ensuring graceful degradation if users have a saved order containing this id.

Key nuances and findings:

- The generic wiring references `#btnExportJSON` and `#importInput`, but at present there are no DOM elements with these ids in the template. This means adding these IDs to the new Actions controls will let the existing generic wiring work without extra code. However, the current generic wiring does not show success toasts; Settings wiring does. We will unify behavior by adding toasts to the generic wiring or by adding specific Actions wiring with toasts.
- Keeping a single source of wiring for each control follows DRY: after the move, the Settings wiring for Export/Import should be removed.
- UX-wise, placing Export/Import in Actions matches user expectations: these are immediate operations, not configuration toggles.

---

### Proposed Design

- Move Export/Import controls from Settings to Actions tab under `#actionsMainBlock` as a compact group.
- Use IDs `#btnExportJSON` and `#importInput` for the Actions controls to leverage existing generic wiring.
- Remove the Settings `#exportImportBlock` UI and its associated wiring `(wireSettingsExportImport)`.
- Update defaults:
  - Remove `exportImportBlock` from `DEFAULT_SETTINGS_IDS`.
  - No changes required for `DEFAULT_TASK_IDS`.
- Ensure consistent feedback on both operations:
  - Show toast on successful export/import.
  - Disable import input during processing (optional enhancement) to avoid double-imports.

Accessibility & UI/UX:

- Buttons should have `aria-label`, keyboard access, and visible focus styles consistent with existing Tailwind classes.
- Import should reset the file input value after completion so the same file can be re-imported if needed.

---

### Step-by-step Implementation Plan

1) Add Export/Import controls to Actions panel
- Inside `#actionsMainBlock`, add a small group:
  - Button `#btnExportJSON` — "Export JSON" (primary style similar to header/action buttons)
  - Label + hidden input `#importInput` with `accept="application/json"` — labeled "Import JSON"

2) Remove Settings Export/Import block
- Remove the entire `#exportImportBlock` markup from Settings.
- Remove `wireSettingsExportImport()` code block that attaches listeners to `#settingsBtnExportJSON` and `#settingsImportInput`.

3) Update defaults and ordering
- Edit `DEFAULT_SETTINGS_IDS` to remove `exportImportBlock`.
- Confirm that `applyPanelOrder` ignores missing ids in persisted orders (it already guards by checking element existence). No migration is necessary.

4) Wiring adjustments (DRY)
- Reuse existing generic wiring for `#btnExportJSON` and `#importInput`. Augment it to show toasts on success to match prior Settings UX.
- Alternatively (if we keep generic wiring minimal), add a small Actions-specific wiring block near `wireActionsPanel` to attach toasts while calling the same helpers. Pick one approach to avoid duplicate listeners. Proposed: enhance the generic wiring with toasts.

5) Sanity and error handling
- Guard all wiring with existence checks and `dataset.wired` flags to prevent duplicate listeners.
- On import, handle JSON parse errors and malformed structures with a user-friendly toast and no-op.

6) Code style and cleanliness
- Keep function names and identifiers in English.
- Avoid duplicating helper logic; keep `exportProjectJSON` and `importProjectJSONFromFile` as the single source of truth.

---

### Manual Test Plan

Prerequisites: Open a project page `/projects/{id}`.

1. Visibility and placement
- Switch to Actions tab. Expect to see Export JSON and Import JSON controls in `Actions`.

2. Export JSON
- Click "Export JSON". Expect a file download named `project-{id}.json` with nodes and edges arrays.
- Open the file and verify its contents are valid JSON with expected fields.

3. Import JSON (append)
- Click "Import JSON", select the previously exported file.
- Expect a success toast and new nodes appended to the current graph (duplicates possible if the same file is imported repeatedly; this mirrors existing behavior).
- Verify no errors are thrown in the console.

4. Regression checks
- Open Settings tab and verify that Export/Import block is removed.
- Reload the page. Confirm Actions tab still shows the controls and they work.

5. Error handling
- Try importing a non-JSON file: expect a user-friendly error toast and no changes.
- Try importing a JSON with missing `nodes` field: expect no crash and a safe no-op with error toast.

6. Accessibility
- Tab to Export button and Import label; ensure they are focusable and operable via keyboard.

---

### Acceptance Criteria

- Export/Import JSON is available in Actions tab and removed from Settings.
- Export triggers a valid JSON download; Import appends nodes per existing logic.
- Success toasts show for both actions; errors show a friendly toast.
- No duplicate listeners; no regressions in other Actions.
- `DEFAULT_SETTINGS_IDS` no longer includes `exportImportBlock`.

---

### Implementation Checklist (living)

- [ ] Add Export/Import controls to `#actionsMainBlock` with ids `btnExportJSON` and `importInput`.
- [ ] Remove `#exportImportBlock` markup from Settings.
- [ ] Remove `wireSettingsExportImport()` wiring block.
- [ ] Update `DEFAULT_SETTINGS_IDS` to remove `exportImportBlock`.
- [ ] Enhance generic wiring to show success toasts on export/import.
- [ ] Validate import parsing and add error toasts on failure.
- [ ] Manual test run per plan above; verify no console errors.
- [ ] Commit changes and update this document with outcomes.

Status Legend: [ ] Planned, [x] Done, [~] In Progress, [!] Blocked

---

### Risks and Mitigations

- Duplicate event wiring: use `dataset.wired` flags and keep a single wiring path post-move.
- Persisted Settings order references removed block: ignored gracefully by existing checks; defaults updated.
- UX confusion if also present in header in the future: keep ids unique and actions scoped to Actions panel unless header controls are reintroduced intentionally.

---

### Notes on Principles

- SOLID/DRY/KISS: reuse helpers; avoid duplicating wiring; keep changes localized.
- Separation of Concerns: markup changes in Actions; Settings cleanup; wiring consolidated.
- UI/UX: clearer placement under Actions; consistent feedback; accessible controls.


