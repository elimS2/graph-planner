## Settings: Backup Scheduler Block Reordering — Roadmap

### Initial Prompt (English)

Make the backup schedule block in the sidebar (on the Settings tab) behave like the other blocks: the other blocks can be reordered (drag to change position), but this one cannot. Implement the same capabilities for it.

— Analyze the Task and project —

Deeply analyze our task and project and decide how best to implement it.

— Create Roadmap —

Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Capture in the document all discovered and tried problems, nuances, and solutions in as much detail as possible, if any. As you progress in implementing this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose, and what decisions were made. For history do not delete items, only update their status and add comments. If, during implementation, it becomes clear that something needs to be added from the tasks — add it to this document. This helps to preserve context, remember what we've already done, and not forget the planned work. Remember that only the English language is allowed in the code and comments, labels of the project. When you write the plan, stop and ask me if I'm okay with starting implementation or if something needs to be adjusted in it.

Include steps for manual testing: what exactly to click through in the UI.

— SOLID, DRY, KISS, UI/UX, etc —

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context and Current Behavior

- The Settings tab in the sidebar contains several blocks (e.g., LOD, Server Info, Env, Visibility, Translation). These blocks are reorderable via a drag handle injected into each block header.
- The Backup Schedule block (id: `scheduleBlock`) exists with a header button `scheduleToggle` and a body `scheduleBody` containing schedule controls and status.
- Observed issue: `scheduleBlock` cannot be reordered like other settings blocks.

### Root Cause Analysis

- Reordering logic is centralized in the client-side script within `app/templates/project.html`:
  - The array `DEFAULT_SETTINGS_IDS` defines which blocks are eligible for ordering and persistence under the key `sidebar.settings.order`.
  - The function `wireReorderablePanel(panelEl, storageKey, defaultIds)` injects drag handles and enables drag-and-drop for blocks whose ids are included in `defaultIds`.
  - The function `applyPanelOrder(panelEl, storageKey, defaultIds)` restores the persisted order, appending any currently missing ids from `defaultIds`.
- Current configuration: `DEFAULT_SETTINGS_IDS = ['lodBlock','serverInfo','envBlock','visibilityBlock','translationBlock']`.
- Missing id: `scheduleBlock` is not included in `DEFAULT_SETTINGS_IDS`, so it does not receive a drag handle and is excluded from the allowed set for drag-and-drop.

### Design Decision

- Minimal, KISS, non-breaking change: include `scheduleBlock` in `DEFAULT_SETTINGS_IDS` so it participates in ordering exactly like other Settings blocks.
- No backend changes required. The change is fully client-side and uses existing ordering persistence (`localStorage`) and DnD wiring logic.
- Persistence behavior: existing saved orders will remain; `scheduleBlock` will be appended at the end on first load (since `applyPanelOrder` merges saved ids with the full default set). Users can then reorder it as desired.

### Affected Areas

- File: `app/templates/project.html` (client script section)
  - Constant `DEFAULT_SETTINGS_IDS`
  - No other structural markup changes needed because `scheduleBlock` already contains a header button with id ending in `Toggle` and a body, matching the pattern used by other blocks.

### Implementation Plan (Step-by-Step)

1) Update reorder whitelist
   - Add `'scheduleBlock'` to `DEFAULT_SETTINGS_IDS` in `app/templates/project.html`.
   - Confirm that the header button id `scheduleToggle` matches the drag handle injection selector `button[id$="Toggle"]`.

2) Verify DnD wiring
   - Ensure `wireReorderablePanel(settingsPanel, ORDER_KEYS.settings, DEFAULT_SETTINGS_IDS)` is called (it is).
   - No changes to `applyPanelOrder` or storage keys.

3) QA: Functional testing (see Manual Test Plan below)
   - Validate handle visibility, drag behavior, persistence, and non-regressions for other blocks.

4) Documentation
   - Keep this roadmap updated: status, decisions, and any edge cases discovered during testing.

### Manual Test Plan

Preconditions: App running locally; `project.html` loads; Sidebar visible.

1) Open Settings tab
   - Click the Settings tab; verify `scheduleBlock` is visible.

2) Handle presence
   - In `scheduleBlock` header, verify a vertical drag handle ("⋮⋮") appears next to the chevron.

3) Drag-and-drop within Settings panel
   - Drag `scheduleBlock` above `lodBlock`; drop. Confirm visual order changes immediately.
   - Drag `scheduleBlock` between other blocks (e.g., between `envBlock` and `visibilityBlock`).
   - Ensure the collapse toggle does not trigger when starting the drag from the handle.

4) Persistence
   - Reload the page. Confirm the order is preserved (via `localStorage` under `sidebar.settings.order`).

5) Non-regression
   - Verify other Settings blocks remain reorderable and functional (collapse/expand, chevrons, content).
   - Verify other panels (Task, Actions) remain unaffected.

6) Accessibility/UX
   - Ensure focus is not stolen when starting a drag from the handle.
   - Ensure keyboard interaction on the header still toggles collapse correctly when not dragging.

### Acceptance Criteria

- `scheduleBlock` has a drag handle identical to other Settings blocks.
- `scheduleBlock` can be reordered within the Settings panel via drag-and-drop.
- The new order persists across reloads using the existing storage key `sidebar.settings.order`.
- No regressions in other blocks’ reordering, collapsing, or content behavior.

### Risks and Mitigations

- Risk: Existing users might not notice that `scheduleBlock` is now reorderable.
  - Mitigation: Subtle affordance via the consistent handle icon; optional release note.
- Risk: Edge case where a user’s saved order contains unknown ids.
  - Mitigation: Current logic already filters to allowed ids and appends missing ones; no change needed.

### Rollback Plan

- Revert the addition of `'scheduleBlock'` in `DEFAULT_SETTINGS_IDS` if any issues arise.

### Timeline and Effort

- Implementation: ~5–10 minutes.
- Testing: ~5 minutes.

### Status Log

- [x] Planned: Add `scheduleBlock` to `DEFAULT_SETTINGS_IDS`.
- [x] Implemented: Code edited and saved.
- [ ] Tested: Manual test plan executed; results recorded.
- [ ] Done: Ready to merge/deploy.

### Notes / Decisions

- No markup changes required; the block already follows the header/body pattern used by the DnD logic, including a header button with id ending in `Toggle`.


