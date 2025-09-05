## Task Panel: Collapsible Groups Roadmap

### Initial Prompt (translated to English)

You wrote (in Russian). Below is an accurate English translation to preserve the original intent in this roadmap file:

"In the sidebar we have Task Panel and Settings. In Settings there are collapsible/expandable groups of settings in blocks. I want the same blocks on the Task Panel tab that can also be collapsed/expanded.

If it is necessary on the Task Panel tab to change the order of displayed blocks or information so that they are structured more logically and merged into collapsible blocks — you can do this.

=== Analyse the Task and project ===

Analyze our task and our project in depth and decide how to implement this in the best way.

==================================================

=== Create Roadmap ===

Create a detailed step-by-step plan for implementing this task in a separate document file. We have the `docs/features` folder for this. If there is no such folder, create it. Document in the file as thoroughly as possible all discovered and tried issues, nuances, and solutions if any. As you progress with implementation of this task you will use this file as a to-do checklist, and you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For historical reasons do not delete items; only update their status and comment. If during implementation it becomes clear that something needs to be added — add those tasks to this document. This will help us keep the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in code and comments, and in project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if anything needs to be adjusted in it.

Include this prompt in the plan (translated into English). You can name it in the plan as something like "Initial Prompt". This is needed to preserve the task context in our roadmap file as precisely as possible without the broken telephone effect.

Also include steps for manual testing, i.e. what needs to be clicked in the interface."


### Current State Summary

- The main project view is rendered by `app/templates/project.html`.
- The sidebar has two tabs: `Task` and `Settings`.
- The `Settings` panel already implements collapsible sections using an accessible toggle pattern with `aria-expanded` and a helper function `wireCollapsibleSection(...)` that persists collapsed state in `localStorage` with dedicated keys.
- The `Task Panel` is currently a flat list of controls and information blocks without collapse/expand affordances. It includes (high-level):
  - Selected node title (inline editable)
  - Link URL field with "open in new tab" toggle and hint
  - Translated title (preview)
  - Selected Node ID, Created At
  - Status (radio buttons), Priority (radio buttons)
  - Hide from board (checkbox)
  - Descendants count
  - Comments section (list), Status History list
  - Comment editor and form
  - Time tracking list and form
  - Costs list and form
  - Delete Node button


### Problem Statement

Bring the `Task Panel` to parity with `Settings` regarding collapsible/expandable sections. Improve structure and grouping for clarity and efficiency, while preserving current behavior and IDs of existing interactive elements to avoid breaking JS logic.


### Design Goals and Principles

- UX parity with `Settings`: same visual toggle affordance, `aria-expanded`, chevron rotation, keyboard support (Enter/Space), and persisted collapsed state in `localStorage`.
- Logical grouping and order to support a top-down workflow: identify selection → edit core fields → set status/priority → adjust visibility/metrics → collaborate (comments/history) → log time/costs → destructive actions.
- Non-breaking change: maintain existing element IDs for inputs, lists, and buttons. Only add wrappers and toggles around them.
- Accessibility: ensure toggles are focusable buttons, with correct ARIA states and keyboard toggling.
- Performance: vanilla DOM only; reuse the existing `wireCollapsibleSection` helper. No additional libraries.
- Simplicity (KISS) and DRY: reuse the existing helper instead of writing a new one; consistent storage key naming, consistent structure per block.


### Proposed Information Architecture (Task Panel)

Order and blocks to introduce, each as a collapsible section with a button toggle and a body:

1) Selection Summary
   - Inline Title (`#selNodeTitle`)
   - Translated Title preview (`#selNodeTitleTranslated`, refresh button)
   - Node ID (`#selNode`), Created At (`#createdAt`)
   - Default: Expanded

2) Linking
   - Link URL (`#selNodeLinkUrl`), "Open in new tab" (`#openInNewTab`), hint (`#linkHint`)
   - Default: Expanded

3) Status & Priority
   - Status radio group (`#statusRadios`)
   - Priority radio group (`#priorityRadios`)
   - Default: Expanded

4) Visibility & Metrics
   - Hide from board (`#hideFromBoard`)
   - Descendants count (`#descCount`)
   - Default: Collapsed

5) Comments
   - Comments list (`#commentsList`)
   - Comment editor (`#commentEditorArea`, toolbar) and form (`#commentForm`)
   - Default: Collapsed

6) History
   - Status History list (`#statusHistory`)
   - Default: Collapsed

7) Time Tracking
   - Time list (`#timeList`), Time form (`#timeForm`)
   - Default: Collapsed

8) Costs
   - Cost list (`#costList`), Cost form (`#costForm`)
   - Default: Collapsed

9) Danger Zone
   - Delete Node button (`#btnDeleteNodePanel`)
   - Default: Collapsed

Storage keys convention for persistence:
- `sidebar.task.selection.collapsed`
- `sidebar.task.link.collapsed`
- `sidebar.task.statusPriority.collapsed`
- `sidebar.task.visibility.collapsed`
- `sidebar.task.comments.collapsed`
- `sidebar.task.history.collapsed`
- `sidebar.task.time.collapsed`
- `sidebar.task.costs.collapsed`
- `sidebar.task.danger.collapsed`


### Implementation Plan (Step-by-step)

1) Introduce collapsible wrappers in `Task Panel` HTML
   - For each block above, wrap existing content into a container `div` with a header `button` (toggle) and a body `div`.
   - Do NOT change IDs of existing input controls/lists/buttons; only add new wrapper IDs like `taskSelectionToggle`, `taskSelectionBody`, etc.
   - Apply consistent classes mirroring `Settings` blocks (rounded, bordered, `p-3`, `bg-white`, `space-y-*`).

2) Reuse the `wireCollapsibleSection` helper
   - Call the same helper for each new task block with dedicated `storageKey`s per the convention above.
   - Ensure calls are executed when `Task` tab is shown (similar to how `Settings` initializes on show). The helper is idempotent; guard with data attribute `data-wired` as already implemented.

3) Default expand/collapse states
   - Apply desired defaults on first run by not pre-hiding bodies in markup; rely on `wireCollapsibleSection` to read `localStorage` and set state.

4) Accessibility and keyboard support
   - Ensure toggle headers are real `<button>` elements with `aria-expanded`, `aria-controls`, and respond to Enter/Space.

5) Styling parity
   - Use the same chevron element with `[data-chevron]` and rotate via inline style transform as in `Settings`.

6) Ensure no breakages
   - Verify all existing JS that queries task panel elements by ID still finds them (unchanged IDs).
   - Verify event listeners on forms and buttons remain attached.

7) Persistence keys
   - Use the `sidebar.task.*.collapsed` keys to persist per-device preferences, not per-node. This matches `Settings` behavior and is simplest.

8) Documentation
   - Update this roadmap with outcomes, decisions, and any deviations.


### Potential Risks and Mitigations

- Risk: Any JS that relied on specific DOM ancestry might be affected by the new wrappers.
  - Mitigation: Keep wrappers shallow and avoid moving elements across different logical blocks unless necessary. Test interactions thoroughly.

- Risk: Collapsed Comments/History blocks may hide useful data by default.
  - Mitigation: Persist user preference. Start core blocks expanded; collaboration/logging blocks collapsed.

- Risk: Increased sidebar height/overflow interactions with the resizer.
  - Mitigation: The sidebar already supports overflow; no additional work expected.


### Manual QA Checklist (click-through scenarios)

Basic navigation
- [ ] Open a project; ensure sidebar is visible.
- [ ] Switch between `Task` and `Settings` tabs; active tab styling is preserved.

Task Panel structure and collapse/expand
- [ ] Verify each of the 9 blocks exists with a header toggle and chevron.
- [ ] Toggle each block open/closed with mouse; content shows/hides accordingly.
- [ ] Toggle with keyboard (focus header → Enter/Space) works; `aria-expanded` flips.
- [ ] Collapsed/expanded state persists after page reload (per block).

Key interactions inside blocks
- [ ] Inline title editing still works and updates the node title.
- [ ] Link URL and "Open in new tab" checkbox behavior unchanged; hint visibility intact.
- [ ] Status and Priority buttons update the node and reflect selection.
- [ ] Hide from board checkbox still toggles visibility.
- [ ] Comments list renders; can submit a new comment with the editor.
- [ ] Status History renders correctly.
- [ ] Time list renders; submitting time works.
- [ ] Costs list renders; submitting cost works.
- [ ] Delete Node button remains functional and is hidden unless applicable.

Edge cases
- [ ] With no node selected, Task Panel shows placeholders without errors.
- [ ] After switching nodes, block states remain as set; content updates to the new node.


### Out of Scope (for this task)

- Changing data persistence model (e.g., per-node collapse states).
- Redesigning styles beyond parity with `Settings`.
- Introducing animations beyond chevron rotation.


### Open Questions

- Do you prefer the `History` block to be grouped together with `Comments` (one combined "Collaboration" block), or kept separate as proposed? — Resolved: keep separate (decision v0.1).
- Should `Visibility & Metrics` be expanded by default, or remain collapsed to keep the top clean? — Resolved: remain collapsed (decision v0.1).
- Is global (per device) persistence sufficient, or do you want per-project persistence keys?

Note on persistence question:
- "Per device" means collapse/expand states are stored in `localStorage` without project scoping; your preference applies across all projects in this browser/profile.
- "Per project" would scope keys by the current project (e.g., include project ID in the storage key) so each project remembers its own sidebar preferences.
- Current plan: keep per-device (simplest, consistent with Settings). We can switch to per-project keys if needed without changing the UI structure.


### TODO / Progress Log

- [x] Create collapsible wrappers for Task Panel blocks in `app/templates/project.html`.
- [x] Wire each block to `wireCollapsibleSection` with `sidebar.task.*.collapsed` keys.
- [x] Verify and adjust block order to match the proposed IA.
- [x] A11y: confirm `aria-expanded` updates and keyboard toggling for all blocks.
- [x] Manual QA: run through all scenarios above and fix any regressions.
- [x] Update this document with results, decisions, and any follow-ups.


### Changelog / Decisions

- v0: Drafted the plan, defined IA, and testing checklist. Awaiting approval to implement.
- v0.1: Decisions recorded
  - Keep `Comments` and `History` as separate blocks (no "Collaboration" merge).
  - `Visibility & Metrics` remains collapsed by default.
  - Persist collapse states per device using `localStorage` keys `sidebar.task.*.collapsed` (project-scoped persistence can be introduced later if requested).
 - v1.0: Implemented collapsible Task Panel with compact UI
   - Added 9 collapsible blocks and wired persistence per device.
   - Reduced paddings/spacing; removed redundant inner headings; smaller comment editor height.
   - Verified keyboard and mouse toggling; states persist across reloads.

### QA Results (v1.0)
- Basic navigation: OK (tabs switch, styling preserved)
- Collapse/expand across all 9 blocks: OK (mouse + keyboard, aria state updates)
- Persistence via localStorage: OK
- Core interactions unaffected: title edit, link URL/new tab, status/priority, hide from board, descendants count
- Collaboration blocks: comments list & editor submit OK; status history OK
- Time/cost: list + submit OK
- Danger Zone: delete button wiring intact (still conditional visibility)


