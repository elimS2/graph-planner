## Add New Status: "discuss" — Roadmap and Design

Status: In Progress
Owner: System
Last Updated: 2025-09-04

### Initial Prompt (translated)

We need to add one more status to our points. We already have statuses: todo, in progress, done, blocked. Add another status "discuss" — meaning "for discussion" — and give it its own color.

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

## 1) Context and Current Behavior

- Data model: `Node.status` is a `String` with default `"planned"` (represents UI label "todo"). No enum constraint.
- Backend: status changes are accepted via `PATCH /api/v1/nodes/<id>` and recorded into `StatusChange` history. Group auto-status (in `recompute_group_status`) currently derives status from children with precedence: blocked > in-progress > done > planned.
- Frontend (in `app/templates/project.html`):
  - Status radio group provides four values: `planned`, `in-progress`, `done`, `blocked` and styles via `getStatusPalette`.
  - Cytoscape node styles color nodes by status with explicit selectors, e.g., `node[status = "planned"]`.
  - Filters include the same status set.
  - Priority-based edge coloring uses only whether a target node is `done` or not; other statuses behave as "not done".

Implications:
- Adding a new status is primarily a frontend task: add it to the radio group, palette, filter, and Cytoscape selector. Backend remains compatible because `status` is a free-form string persisted as-is.
- Group recomputation can treat `discuss` like `planned` (neutral, not in-progress, not blocked, not done). No DB migration required.

## 2) Goals and Non-Goals

Goals:
- Introduce new status `discuss` with a distinctive color and full UI support.
- Keep behavior consistent: `discuss` is considered "not done" for edge coloring and path computation.
- Maintain accessibility and responsive layout in the status control.

Non-Goals:
- Changing backend data types or adding enums.
- Altering priority-path logic or edge styling semantics.

## 3) Design Decisions

3.1 Status semantics
- `discuss` = an item pending discussion. Treated like `planned` in computations: not `done`, not `in-progress`, not `blocked`.
- Group status derivation remains unchanged; `discuss` falls into the default bucket that maps to `planned` for groups when there are mixed non-terminal statuses.

3.2 Color palette
- Choose a distinct, accessible color different from existing ones:
  - Discuss (violet): solid `#8b5cf6` (violet-500), soft `#f5f3ff` (violet-50), border `#7c3aed` (violet-600).
  - Contrast checked against white text for the active state.

3.3 UI/UX adjustments
- Add a fifth radio to the status group with value `discuss` and label `discuss`.
- Update grid layout to accommodate five options (e.g., `grid-cols-3 md:grid-cols-5`).
- Extend `getStatusPalette` and Cytoscape style selectors with `discuss` color.
- Add `Discuss` option to the status filter dropdown.

## 4) Implementation Plan (Step-by-Step)

Frontend (`app/templates/project.html`):
1. Status control
   - Add a new button to `#statusRadios`: `data-value="discuss"`, label `discuss`.
   - Update container grid classes to fit five options responsively.
2. Palette
   - Extend `getStatusPalette(val)` with `case 'discuss'` returning the violet palette.
3. Graph styles
   - Add Cytoscape selector: `{ selector: 'node[status = "discuss"]', style: { 'background-color': '#8b5cf6' } }` near other status selectors.
4. Filters
   - Add an `<option value="discuss">Discuss</option>` to the status filter dropdown.
5. Misc
   - Ensure places that default to `planned` remain unchanged; `discuss` behaves as "not done" in path coloring (no change needed).

Backend (optional doc-only updates):
6. Update the docstring of `recompute_group_status` to mention `discuss` is treated like `planned` (no code change required).

Documentation:
7. Update this roadmap Work Log as steps are implemented.

## 5) Manual Testing Checklist (UI Click-Through)

Preparation
- Open a project with a few nodes and edges.

Status Control
- Select a node; verify the status panel shows five buttons including `discuss`.
- Click `discuss`; verify:
  - Button styles update to violet active state.
  - Node color changes to violet immediately on the graph.
  - PATCH request succeeds; status history lists the change to `discuss`.

Filters
- Use the status filter dropdown; choose `Discuss` and verify only `discuss` nodes remain visible in list/search views where applicable.

Graph Semantics
- With a high/critical neighbor targeting a `discuss` node, verify edge coloring logic behaves the same as for `planned` (i.e., considered not done).
- Change node from `discuss` to `done`; verify edge recoloring updates instantly (existing behavior).

Responsiveness & A11y
- Resize window; ensure the status radio grid remains readable and keyboard navigation works.

## 6) Risks and Mitigations

- Visual contrast: validate violet on white and white on violet meets accessibility; adjust to indigo if needed.
- Layout overflow: ensure five options do not wrap awkwardly on small screens; tune grid columns.
- Consistency: verify all status-dependent UI (filtering, legends, history) gracefully includes `discuss`.

## 7) Acceptance Criteria

- [ ] New `discuss` status is selectable, persisted, and visible in history.
- [ ] Node with `discuss` shows violet color on the canvas.
- [ ] Status filter includes and filters by `Discuss`.
- [ ] No backend migrations; no console errors; lints pass.

## 8) Work Log (Changelog)

- [x] 2025-09-04 — Draft roadmap created and approved.
- [x] 2025-09-04 — Implemented UI changes: added `discuss` status button, palette, Cytoscape selector, and filter option in `app/templates/project.html`.


