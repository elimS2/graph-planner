## Sidebar Panel Blocks: Reorderable Sections

### Initial Prompt (translated to English)

We have a sidebar, the sidebar has tabs. Inside the tabs there are collapsible blocks; I want the order of these blocks to be configurable.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how this is best implemented.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Record in the document as thoroughly as possible all discovered and tried problems, nuances and solutions, if any. As you progress with this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what solutions were chosen. For history, do not delete items; you may only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks – add it to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt that I wrote in the plan, but translate it into English. You can name it something like "Initial Prompt" in the plan document. This is needed in order to preserve in our roadmap file the exact context of the task statement without the "broken telephone" effect.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.

Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.

Use Best Practices.

---

### Context and Current Behavior

- The sidebar is defined in `app/templates/project.html` as an `<aside id="sidebar">` with two tabs: `#tabTask` and `#tabSettings`.
- Each tab contains multiple collapsible blocks. The Task tab (`#taskPanel`) currently includes blocks such as:
  - `#taskSelectionBlock`, `#taskLinkBlock`, `#taskStatusPriorityBlock`, `#taskVisibilityBlock`, `#taskCommentsBlock`, `#taskHistoryBlock`, `#taskTimeBlock`, `#taskCostsBlock`, `#taskDangerBlock`.
- The Settings tab (`#settingsPanel`) includes blocks such as:
  - `#serverInfo`, `#envBlock`, `#exportImportBlock`, `#visibilityBlock`, `#translationBlock`, and a `#lodBlock`/`#zoomToggle` section.
- Collapsible behavior is wired via a helper like `wireCollapsibleSection(...)` and the collapsed state for each block is persisted in `localStorage` under stable keys (e.g., `sidebar.task.selection.collapsed`, `sidebar.settings.env.collapsed`).
- The active tab is also persisted in `localStorage` (`sidebarTab`), and the sidebar has a resizer and visibility toggle whose states also persist.

Implication: The project already centralizes sidebar logic in a single template with unobtrusive JS, and it uses `localStorage` to persist UI state. No server API for per-user sidebar preferences exists yet. Implementing block order persistence can therefore be done fully client-side, consistent with current architecture.

### Goals

- Allow users to reorder blocks within each tab (Task and Settings) via intuitive drag-and-drop using a small, discoverable handle in the block header.
- Persist the block order per tab in `localStorage` and re-apply on page load/tab switch.
- Preserve each block’s collapsed/expanded state independent of its position.
- Minimize code footprint and keep logic self-contained in `project.html` (no server or DB changes).
- Maintain accessibility and do not break existing keyboard navigation or collapse toggles.

### Non-Goals (initial scope)

- Cross-device/cloud sync of block order (no server persistence initially).
- Reordering across tabs (blocks stay within their tab).
- Reordering internal elements within a block (only block-level reorder).
- Adding new settings pages beyond the project view sidebar.

### UX and Interaction Design

- Each block header gets a small drag handle (e.g., a 12–16px "grip" icon) on the right side of the header row.
  - Dragging is initiated only when the user drags the handle, so clicking the header still toggles collapse.
- While dragging, a placeholder indicates the potential drop position with a subtle highlight and spacing.
- Dropping moves the block to the new position instantly; the new order is saved.
- Collapsed blocks are still draggable.
- Optional (phase 2): keyboard reordering via Up/Down when the header is focused, with ARIA announcements.

### Data Model and Persistence

- Order is stored as an array of block IDs per tab in `localStorage`:
  - `sidebar.task.order` → e.g., `["taskSelectionBlock","taskLinkBlock", ...]`
  - `sidebar.settings.order` → e.g., `["serverInfo","envBlock", ...]`
- Default order is defined by initial DOM order and used when no saved order is present or when IDs are missing.
- Robustness: unknown IDs in saved order are ignored; new, previously unknown IDs are appended in default order.

### Technical Design

1) Identify block containers:
   - In Task tab: any direct children of `#taskPanel` with ids ending in `Block` (e.g., `#taskSelectionBlock` ... `#taskDangerBlock`).
   - In Settings tab: `#serverInfo`, `#envBlock`, `#exportImportBlock`, `#visibilityBlock`, `#translationBlock`, and `#lodBlock` if present.

2) DOM attributes and structure:
   - Add a drag handle element inside each header button (e.g., `<span data-drag-handle>` with a grip icon) and set `cursor: grab` on hover.
   - Set `draggable="true"` on each block container. For accessibility, consider `aria-grabbed` updates on drag start/end.

3) Drag and drop behavior (HTML5 DnD / Pointer events):
   - On drag start (from the handle): mark the source block id (e.g., `data-drag-id`), add a `dragging` class.
   - On drag over other block containers within the same panel: compute insert position (before/after) based on cursor Y.
   - Show a placeholder style on the target position.
   - On drop: move the source block in the DOM to the computed position, remove placeholder, clear dragging class.
   - Save the new order via `savePanelOrder(panelEl, storageKey)`.

4) Initialization and application of saved order:
   - On `showTask()` / `showSettings()`, after wiring collapsibles, call `applyPanelOrder(panelEl, storageKey, defaultIds)`.
   - `applyPanelOrder` reorders child nodes to match saved order, then appends any missing IDs in default sequence.
   - Idempotent: safe to call multiple times.

5) Persistence helpers:
   - `getPanelIds(panelEl)` → returns array of block container IDs in current DOM order.
   - `loadOrder(storageKey)` / `saveOrder(storageKey, idsArray)` → read/write JSON to `localStorage`.
   - `applyPanelOrder(panelEl, storageKey, defaultIds)` → orchestrates load/merge/apply.

6) Accessibility considerations:
   - Keep header button semantics intact; drag starts only from handle element to avoid conflicting with collapse toggle.
   - Provide visible focus outlines for the handle; optional `aria-label="Reorder section"`.
   - Phase 2 (optional): keyboard reorder with announcements (e.g., `aria-live`), if needed.

7) Styling:
   - Use Tailwind utility classes for handle and placeholder visuals (no extra CSS files).
   - Keep animations subtle to avoid jank.

### Edge Cases

- Collapsed sections: reordering works the same; no need to auto-expand on drag.
- Touch devices: HTML5 DnD support varies; MVP focuses on desktop. Phase 2 can add pointer-based drag with long-press.
- New sections in future: automatically included; their IDs appended when not present in saved order.
- Unknown/missing IDs in saved data: ignored gracefully.

### Implementation Plan (Step-by-Step)

1) Read-only discovery (done)
   - Locate sidebar structure in `app/templates/project.html` and list block IDs for Task and Settings tabs.

2) Add persistence helpers in `project.html` (script section)
   - `loadOrder`, `saveOrder`, `getPanelIds`, `applyPanelOrder` with defensive coding and try/catch around `localStorage`.

3) Add drag handles and `draggable` attributes
   - Insert a handle span in each header button (both Task and Settings blocks) with proper classes.
   - Set `draggable="true"` on the block containers.

4) Wire drag-and-drop events
   - Use event delegation on the panel container to manage `dragstart`, `dragover`, `dragleave`, `drop`, `dragend`.
   - Ensure only the handle initiates drag; preventDefault appropriately.

5) Apply saved order on tab show
   - In `showTask()` and `showSettings()`, call `applyPanelOrder` after collapsible wiring.
   - Define and pass default ID arrays in code for determinism.

6) Manual tests (see checklist below)

7) Optional enhancements (future)
   - Keyboard reorder; per-project scoped keys; "Reset order" button per tab.

### Manual Test Checklist

Task tab
1. Open `/projects/<id>`; ensure the sidebar is visible and Task tab is active.
2. Drag `Selection` block below `Linking`; drop. Verify the order changed.
3. Reload the page. Verify the changed order persists.
4. Collapse `Status & Priority`; drag it above `Selection` while collapsed. Verify it moves and remains collapsed.
5. Toggle several blocks; verify collapse states persist independently of order.

Settings tab
6. Switch to Settings tab. Drag `Server Info` below `.env`. Verify order changes.
7. Reload the page. Verify Settings order persists and Task order remains as previously set.
8. Use existing features (filter `.env`, restart server). Verify no regressions.

General
9. Resize the sidebar and toggle its visibility. Verify drag-and-drop still works afterward.
10. Verify that clicking the header (not the handle) still toggles collapse, and does not start a drag.

### Risks, Assumptions, Mitigations

- Risk: Drag conflicts with collapse click. Mitigation: drag only via a small handle element; stop propagation properly.
- Risk: HTML5 DnD limitations on touch devices. Mitigation: desktop-first; plan pointer-based fallback later.
- Assumption: Block containers have stable IDs; future renames will update default arrays accordingly.
- Assumption: `localStorage` available; if not, feature still functions for the session without persistence (no hard failure).

### Rollback Plan

- Remove the drag-and-drop event wiring and handle elements in `project.html`.
- Remove order application calls; no server-side impact; zero data migration.

### Acceptance Criteria

- Users can reorder blocks within Task and Settings tabs via drag handle.
- Order persists across page reloads per tab via `localStorage`.
- Collapsed state persists and is independent of order.
- No regressions to existing sidebar functions (collapse, env table, restart, resizer, etc.).

### Tasks (Living Checklist)

- [x] Analyze current sidebar structure and identify block IDs.
- [ ] Add persistence helpers for order management in `project.html`.
- [ ] Add drag handles to block headers and set containers as draggable.
- [ ] Implement drag-and-drop with placeholder and reorder logic.
- [ ] Apply saved order on tab activation for both tabs.
- [ ] Manual testing on Windows/Chrome and Firefox per checklist.
- [ ] Optional: add "Reset order" button and/or keyboard reordering.

### Open Questions

- Scope of persistence: Should order be global or per project? MVP proposes global keys (`sidebar.task.order`, `sidebar.settings.order`) for simplicity; per-project scoping can be added later if needed.
- Mobile support: Should we prioritize pointer-based drag for touch devices in MVP?

### Notes on Code Quality and Principles

- Keep functions small, cohesive, and testable (KISS, SoC).
- Avoid duplication (DRY): shared helpers reused for both tabs.
- Clear naming: `applyPanelOrder`, `saveOrder`, `getPanelIds`, etc.
- Accessibility: no degradation in keyboard navigation; consider phase-2 improvements.

### Next Step

Awaiting approval to proceed with implementation according to this roadmap.


