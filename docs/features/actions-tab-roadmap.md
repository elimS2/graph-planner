## Actions Tab in Sidebar — Roadmap

### Initial Prompt (translated)

Add a third sidebar tab called "Actions" alongside the existing "Task Panel" and "Settings" tabs. Populate the new "Actions" tab by duplicating appropriate action buttons from the header that conceptually belong there.

Analyze the task and the project in depth and decide on the best implementation approach.

Create a detailed, step-by-step plan in a separate document file under docs/features. If such a folder does not exist, create it. Document all identified or tried issues, nuances, and solutions. During implementation, use this file as a todo checklist, update it, and record what was done, how it was done, any problems encountered, and the decisions taken. Do not delete items; only update their status and comment. If new subtasks emerge, add them here to preserve context.

Include manual test steps describing exactly what to click in the UI.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

After writing the plan, stop and ask for confirmation to start implementing or adjust the plan.

---

### Context Snapshot

- Project template of interest: `app/templates/project.html`
- Existing sidebar tabs: `Task` and `Settings`
- Header/toolbar actions available:
  - `btnAddNode`, `btnAddEdge`, `btnCriticalPath`, `btnGroup`, `btnUngroup`, `btnCollapse`, `btnExpand`, `btnFit`, `btnScreenshot`, `btnHelp`, `btnResetView`, `btnToggleSidebar`
- Sidebar uses localStorage keys for tabs and collapsible sections, e.g. `sidebarTab`, `sidebar.task.*`, `sidebar.settings.*`

### Proposed Scope for Actions Tab

- Create a third tab button `Actions` near `Task` and `Settings`.
- Add a dedicated panel `#actionsPanel` controlled by the new tab.
- Populate it with a curated subset of header controls that are frequent graph actions and context-appropriate in the sidebar.

Proposed buttons to include initially:
- Graph view: `Fit`, `Reset View`
- Structure: `Group`, `Ungroup`, `Collapse`, `Expand`
- Utilities: `Screenshot`

Buttons now available in Actions as well (duplicated):
- Creation: `+ Node`, `+ Edge`
- Analysis: `Critical Path`
- Graph view: `Fit`, `Reset View`
- Structure: `Group`, `Ungroup`, `Collapse`, `Expand`
- Utilities: `Screenshot`

Buttons that remain header-only for now:
- Help/Onboarding: `Help`
- Layout/Chrome: `Toggle Sidebar` (controls the sidebar itself)

Rationale:
- Actions tab consolidates frequent actions. Creation and analysis are also exposed here for convenience, while still present in the header. Help and Sidebar toggle remain header-only.

### Implementation Plan (Step-by-step)

1) Add Actions tab UI
- Add a new button `#tabActions` next to `#tabTask` and `#tabSettings`.
- Create a container `#actionsPanel` similar to `#taskPanel` and `#settingsPanel`, initially hidden.
- Update tab switching logic to handle three tabs: Task | Actions | Settings.
- Persist selected tab with localStorage key, extend values: `task`, `actions`, `settings`.

2) Move/duplicate wiring for action buttons
- Do not remove header toolbar buttons; duplicate their behaviors in the new panel.
- For each selected action (Fit, Reset View, Group, Ungroup, Collapse, Expand, Screenshot, + Node, + Edge, Critical Path), add a mirrored button in `#actionsPanel`.
- Wire click handlers to call the same underlying functions used by header buttons (reuse functions; avoid duplicating logic inline).

3) Refactor for DRY where needed
- If header buttons currently inline-call logic, extract shared functions (e.g., `performFit()`, `performGroup()`, etc.) in the same script scope of `project.html`.
- Bind both header and actions-tab buttons to these functions.

4) Accessibility and UX
- Use consistent button styles and size as in header or existing sidebar buttons (text size likely `text-xs`/`text-sm` for sidebar).
- Provide tooltips (`title`) and `aria-label`s.
- Respect existing keyboard shortcuts; do not conflict.
- Respect disabled/hidden states (e.g., actions that require a selection should be disabled when no node is selected). If such disable logic isn’t present, add minimal state checks.

5) Persistence and layout
- Ensure localStorage keys are not clashing with existing ones. New keys: `sidebar.actions.order` (optional future), `sidebarTab=actions` for last selected.
- Ensure the resizer logic and hidden sidebar states work seamlessly with the new tab.

6) Actions layout and header visibility controls (NEW)
- Enforce one button per row inside `#actionsPanel` for readability:
  - Use a vertical stack layout (e.g., `flex flex-col gap-2`), or a `grid grid-cols-1 gap-2` container. Buttons should be full-width or visually aligned.
- For each action row, render a compact checkbox "Show in header" to control whether the corresponding header button is visible:
  - Persist preferences in `localStorage` under a namespaced map, e.g., `headerVisibility` with keys like: `actions.header.show.btnAddNode`, `actions.header.show.btnAddEdge`, etc. Value: `'1'|'0'`.
  - On page load, apply visibility by toggling `classList.add('hidden')` on header buttons when preference is `'0'` (do not remove them from the DOM to keep keyboard shortcuts and code paths stable).
  - Changes should take effect immediately when the checkbox is toggled and persist across reloads.
- Keep implementation DRY by maintaining an action registry:
  - Example structure: `{ id: 'btnAddNode', panelId: 'btnAddNodePanel', headerId: 'btnAddNode', label: '+ Node', showInHeaderKey: 'actions.header.show.btnAddNode', defaultShowInHeader: true }`.
  - Iterate the registry to wire both the mirrored actions and the header-visibility checkboxes.

7) Optional: Defaults and reset
- Provide a small "Reset to defaults" control within Actions to restore header visibility preferences to the defaults defined in the registry.

8) Testing Plan (Manual)
- Start server, open a project page.
- Switch between `Task`, `Actions`, `Settings`; ensure the correct panel shows and persists on reload.
- In Actions tab:
  - Click `Fit`: graph viewport fits.
  - Click `Reset View`: resets zoom and pan to default.
  - Select multiple nodes → `Group`: nodes grouped. Then `Ungroup`: group removed.
  - Select a parent node with children → `Collapse` hides descendants; `Expand` shows them.
  - Click `Screenshot`: PNG is downloaded or a new image opens.
  - Ensure only one button per row is visible and the layout remains tidy on narrow widths.
  - Toggle "Show in header" for `+ Node`, `+ Edge`, `Critical Path`, `Fit`, etc.: header buttons should appear/disappear immediately and persist after reload.
  - Verify keyboard shortcuts (n, e, f) still work even when respective header buttons are hidden (we keep buttons in DOM with `hidden` class).
- Verify header buttons still work identically.
- Verify no console errors and performance is unchanged.

7) Rollback Plan
- If issues arise, temporarily hide `#tabActions` and `#actionsPanel` with CSS `hidden`, leaving header behavior intact.

### Risks / Considerations
- Inline logic duplication could lead to drift; mitigate by extracting shared functions.
- Some actions may depend on selection/graph state; provide graceful no-op with user feedback.
- Ensure mobile/narrow layouts keep the sidebar usable.
- Keep header buttons in the DOM and toggle visibility via `hidden` class to preserve keyboard handlers that reference button IDs.
- Ensure registry keys remain stable to avoid orphaned localStorage entries across refactors.

### Todos and Status Log

- [ ] Add `#tabActions` button in sidebar header area
- [ ] Add `#actionsPanel` container and basic layout
- [ ] Wire tab switching for three tabs and persist `sidebarTab`
- [ ] Identify and extract shared action functions from header handlers
- [ ] Add mirrored buttons for Fit, Reset View, Group, Ungroup, Collapse, Expand, Screenshot, + Node, + Edge, Critical Path
- [ ] Bind actions-tab buttons to shared functions
- [ ] Add accessibility attributes and consistent styles
- [ ] Add disabled-state logic based on selection where applicable
- [ ] Enforce single-column layout for Actions buttons
- [ ] Add header visibility checkboxes and persistence
- [ ] Add reset-to-defaults for visibility preferences (optional)
- [ ] Test manually per plan
- [ ] Update this document with findings and any design adjustments

### Notes / Decisions
- Keep creation and analytic actions in the header to reduce sidebar cognitive load.
- If users request, we can optionally add `+ Node` and `+ Edge` to Actions later behind a preference.


