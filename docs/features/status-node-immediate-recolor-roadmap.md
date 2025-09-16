## Immediate Node Dot Recolor While Selected — Roadmap and Design

### Initial Prompt (translated)

There is the following problem: if we click on a dot on the board and then in the sidebar task panel choose its current status, for example set Done or Discuss, the color of the dot changes only when we remove focus from the dot. I want it to change immediately.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, extensive step-by-step plan for implementing this task in a separate document file. We have the folder docs/features for this. If there is no such folder, create it. Record in the document, as thoroughly as possible, all discovered and tried issues, nuances, and solutions, if any. As you progress with the implementation of this task, you will use this file as a todo check-list, updating this file and documenting what is done, how it is done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and comment. If, during implementation, it becomes clear that something needs to be added from the tasks — add it to this document. This will help us preserve the context window, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in code, comments, and project labels. When you finish writing the plan, stop and ask me if I agree to start implementing it or if anything needs to be adjusted in it.

Include this prompt that I wrote in the plan itself, but translate it into English. You can name it something like "Initial Prompt" in the plan document. This is needed to preserve in our roadmap file the context of the task statement as precisely as possible, without the "broken telephone" effect.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### 1) Context and Current Behavior

- Frontend: `app/templates/project.html` renders the graph using Cytoscape.
- Status coloring for nodes is defined via Cytoscape selectors:
  - `node[status = "planned" | "done" | "in-progress" | "discuss" | "blocked"]` set `background-color` accordingly.
  - `node:selected` adds border and overlay, but does not set `background-color`.
- The Task Panel status radio group (element `#statusRadios`) handles clicks in `wireStatusRadios()`:
  - On change, it `PATCH`es `/api/v1/nodes/:id`, updates the node's `data('status')`, then calls `refreshEdgeTargetFlags(selectedNodeId)` and `recomputePriorityPaths()`.
  - If the clicked option equals the already active one (`aria-checked="true"`), it currently short-circuits early and returns without touching Cytoscape node data or forcing a restyle.

Observed effect: when the node is selected and the user clicks a status (sometimes even the same status), the dot color appears to update only after the node loses focus (unselect). This suggests either (a) a missing refresh when value is "no-op", or (b) Cytoscape style not being recomputed immediately in this edge case.

### 2) Root Cause Hypothesis

- For the case where the user clicks the already-selected status value, our handler returns early and does not update node data nor force any style refresh. If for any reason the visible fill color hasn't synced (rare timing or previous state), it won't refresh until another event (like deselection) triggers a re-style.
- Even when the status actually changes, we rely on data-driven restyle, which should be immediate. To make behavior robust in all cases, we will ensure we always trigger a consistent UI refresh path regardless of whether the status value changed.

### 3) Goals and Non-Goals

Goals:
- Node dot background color should reflect the selected status immediately, even while the node remains selected.
- Clicking the same status again should also refresh visuals (idempotent, no backend call).
- Keep the solution small, clean, and maintainable (KISS, DRY).

Non-Goals:
- No backend changes.
- No change to selection UX or status semantics.

### 4) Design Decisions

4.1 Always run a lightweight visual refresh on status radio clicks
- If the value didn't change (already active):
  - Keep early return from network call, but before returning, force a local UI sync:
    - Update Cytoscape style by calling `cy.style().update()` and then invoke `refreshEdgeTargetFlags(selectedNodeId)` and `recomputePriorityPaths()` to keep all visuals consistent.
    - Alternatively (if needed), set the same value again on the node data to ensure a restyle tick; however, `cy.style().update()` should suffice and avoids data churn.

4.2 Keep the existing path when the value changes
- When the value changes, keep the current flow: `PATCH` → update `n.data('status', ...)` → `refreshEdgeTargetFlags()` → `recomputePriorityPaths()`.

4.3 Do not alter styles order
- Our Cytoscape style order already places `node[status=...]` after `node:selected`, so status color wins; keep this ordering intact.

### 5) Step-by-Step Implementation Plan

Frontend (`app/templates/project.html`):
1. In `wireStatusRadios()` click handler, modify the branch for `aria-checked === 'true'`:
   - After `setRadioGroupValue(grp, value)`, execute:
     - `const n = cy.getElementById(selectedNodeId); if (n && n.nonempty()) { /* no data change needed */ }
     - `try { cy.style().update(); } catch {}`
     - `refreshEdgeTargetFlags(selectedNodeId);`
     - `recomputePriorityPaths();`
   - Then `return;` as before (no network call).
2. Keep the changed-value path untouched, ensuring we still update `n.data('status', ...)` and call the same helpers afterward.
3. Sanity-check that no other status update paths skip a visual refresh.

Docs/Changelog:
4. Update this roadmap's Work Log as steps are completed.

### 6) Manual Testing Checklist (UI Click-Through)

Preparation
- Open a project and ensure there is at least one node on the board.

Happy Path — Status Change
- Click a node to select it.
- In the Task Panel, click a different status (e.g., Planned → Done, or In-Progress → Discuss).
- Expected: node dot background color updates immediately without losing selection.

Idempotent Click — Same Status
- With the node still selected and showing a given status, click the same status button again.
- Expected: node dot background color stays correct and re-applies instantly (no delay until deselection).

Regression Check
- Switch between various statuses multiple times; verify no flicker, no delay, no console errors.
- Ensure edges still reflect status-dependent logic (if applicable) via `refreshEdgeTargetFlags` and `recomputePriorityPaths`.

### 7) Risks and Mitigations

- Risk: Forcing a global `cy.style().update()` might be considered heavier than necessary.
  - Mitigation: It is very fast for our graphs. If needed, we can optimize later to restyle only affected elements.
- Risk: Over-refreshing could interfere with ongoing animations.
  - Mitigation: Our usage is on discrete user clicks; negligible impact.

### 8) Acceptance Criteria

- [ ] Changing status while a node is selected updates the dot color immediately.
- [ ] Clicking the same status again keeps the dot color immediately correct (no wait for deselection).
- [ ] No backend changes; no console errors; performance unaffected.

### 9) Work Log

- [ ] 2025-09-16 — Roadmap drafted.
- [ ] 2025-09-16 — Implement handler update in `wireStatusRadios()`.
- [ ] 2025-09-16 — Manual verification on Windows/Chrome and Firefox.

### 10) Additional Issue: Selected Node Border Appears Blue on Small Dots

Observed behavior:
- When a node is small, on selection the node appears blue regardless of status, because the selection border and overlay use a static blue (`#0ea5e9`). This can mislead the user into thinking the status is "planned" (sky/blue) when it's not.

UX goals:
- Preserve strong selection affordance while keeping hue consistent with the node's status.
- Maintain sufficient contrast and accessibility.

Proposed solutions (pick A as primary):

Solution A — Status-aware selection styling (preferred, simple, DRY):
- Replace the single generic `node:selected` color with status-specific selectors that override the border and overlay hues to the darker tone of the current status palette.
- Mapping (aligns with existing `getStatusPalette`):
  - planned: border/overlay `#0ea5e9`
  - in-progress: border/overlay `#d97706`
  - discuss: border/overlay `#7c3aed`
  - done: border/overlay `#16a34a`
  - blocked: border/overlay `#dc2626`
- Keep `border-width` and `overlay-opacity` as-is; only hue changes.
- Benefits: no runtime computation required; purely selector-based; clear precedence.

Solution B — Programmatic selection tint (deferred option):
- On node selection event, set a `data('selHue')` or directly write `border-color` and `overlay-color` via JS from `getStatusPalette`.
- Requires listening to selection/deselection events and updating per-node styles. More code paths; not needed if A suffices.

Implementation Plan (Solution A):
1. Keep `node:selected` rule but remove hard-coded blue `border-color`/`overlay-color` (retain width and text outline). Example: set only `border-width`, `border-opacity`, `text-outline-...`, `overlay-opacity`.
2. Add more specific rules placed after the base `node:selected`:
   - `node:selected[status = "planned"]` → `border-color` + `overlay-color` `#0ea5e9`
   - `node:selected[status = "in-progress"]` → `#d97706`
   - `node:selected[status = "discuss"]` → `#7c3aed`
   - `node:selected[status = "done"]` → `#16a34a`
   - `node:selected[status = "blocked"]` → `#dc2626`
3. Verify selector precedence: status-specific selected rules must come after the generic `node:selected`.
4. Optional: if label contrast suffers on dark overlays, slightly increase `text-outline-width` from 2 → 3 for tiny nodes only, or keep as-is if readable.

Manual Testing Addendum:
- Select a very small node in each status and verify the selection border/overlay hue matches the status hue (darker tone), not blue.
- Toggle statuses while selected; border hue updates immediately with status.
- Ensure the node color and selection affordance are distinct and readable.

Acceptance Criteria (Addendum):
- [ ] Selected node border/overlay hue matches node status hue.
- [ ] Small nodes do not appear blue unless their status is planned.
- [ ] No regressions in selection visibility or performance.

Work Log (Addendum):
- [ ] 2025-09-16 — Add status-aware `node:selected[...]` rules to Cytoscape style.


