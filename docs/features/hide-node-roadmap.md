## Hide Node Feature — Roadmap and Design

### Initial Prompt (translated)

Add a “hide” property to points (nodes), and add a toggle in the task panel. By default, a point is displayed, but it can be hidden; when hidden, it stops being displayed on the board.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in as much detail as possible all discovered and tried problems, nuances, and solutions, if any. As you progress with the implementation of this task, you will use this file as a todo check-list, you will update this file and document what is done, how it is done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and comment. If during implementation it becomes clear that something needs to be added from the tasks — add it to this document. This will help us preserve the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in code, comments, and project labels. When you finish writing the plan, stop and ask me if I agree to start implementing it or if anything needs to be adjusted in it.

Include in the plan steps for manual testing, i.e. what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### 1) Context and Current State

- Backend: Flask app with SQLAlchemy models and Alembic migrations.
- Models: `app/models/__init__.py` defines `Node` with fields such as `status`, `is_group`, `priority`, etc., and `NodeLayout` for positions. There is no hidden flag yet.
- API: Graph endpoints in `app/blueprints/graph/routes.py`:
  - `GET /api/v1/projects/{project_id}/nodes` returns nodes (optionally attaches positions and translations).
  - `PATCH /api/v1/nodes/{id}` updates a node via `NodeSchema(partial=True)`.
  - `POST /api/v1/nodes/{id}/position` persists coordinates.
  - `GET /api/v1/projects/{project_id}/edges` returns edges.
- Serialization: `app/schemas/__init__.py` defines `NodeSchema`, currently without a hidden property.
- Frontend: `app/templates/project.html` renders Cytoscape.js graph with a Task Panel (sidebar). Nodes and edges are loaded separately and composed client-side in `toElements`. Filtering: text search and status-based opacity tweaks; LOD also hides some nodes by display style, but there is no persistent hide feature.

Implications:
- Hiding a node should remove it from the board by default. We must provide a way to toggle the flag in the Task Panel. Consider discoverability and recovery (a way to unhide).

### 2) Goals and Non-Goals

Goals:
- Add a persistent boolean flag on nodes indicating whether the node is hidden from the board.
- Expose the flag via API (read/write) and default server responses to exclude hidden nodes from the standard board view.
- Provide a Task Panel toggle to set/unset the hidden state, with immediate UI feedback.

Non-Goals (for this iteration):
- Complex hidden states for groups (e.g., auto-hiding descendants recursively). We will define a simple policy first (see below) and iterate later if needed.
- Dedicated “Hidden items” management UI. We will note an optional global “Show hidden” toggle for recovery, but it can be deferred if not required.

### 3) Detailed Requirements and Acceptance Criteria

- Data model: A new boolean field `is_hidden`, default `false`, non-nullable, on `Node`.
- API behavior (default): `GET /projects/{project_id}/nodes` MUST NOT include nodes where `is_hidden = true` by default.
- API behavior (optional): add `?include_hidden=1` query support to include the hidden nodes in response for recovery workflows and admin tools.
- Serialization: `NodeSchema` includes `is_hidden` for dump/load (partial allowed on PATCH).
- Task Panel: add a toggle labeled “Hide from board”.
  - Default unchecked for new nodes.
  - When toggled on, send `PATCH /api/v1/nodes/{id}` with `{ "is_hidden": true }`, remove the node from Cytoscape immediately after success.
  - When toggled off, send `PATCH ... { "is_hidden": false }`. To allow unhiding, a discoverability approach is needed (see UX below).
- Edges: No server change required. Cytoscape will ignore edges with missing endpoints.
- Performance: No measurable degradation on large graphs. Adding a boolean column and simple WHERE clause is O(1) overhead.
- Backward compatibility: Existing clients without the toggle keep working; they simply won’t see hidden nodes (server default).

Acceptance tests (high level):
- Creating a node → visible by default.
- Toggling “Hide from board” → node is removed from the board without errors; refresh persists the state.
- With `?include_hidden=1` enabled (if implemented), hidden nodes appear distinctly styled; user can unhide from Task Panel.

### 4) Design Decisions

4.1 Data Model
- Add `Node.is_hidden: bool = False, not null` via Alembic migration with default at DB level.

4.2 API
- Update `NodeSchema` to include `is_hidden`.
- `GET /projects/{id}/nodes`: by default filter with `.filter_by(project_id=..., is_hidden=False)`.
- Optional: `include_hidden` query parameter (truthy values: `1`, `true`, `yes`) to return both hidden and visible nodes, with a field indicating hidden state for client distinction.
- `PATCH /nodes/{id}`: allow `{ "is_hidden": <bool> }`. Keep current status history behavior unchanged (hiding is orthogonal to status transitions).

4.3 UI/UX (Task Panel in `project.html`)
- Insert a checkbox switch below Status, label: “Hide from board”.
- When selected node changes, reflect its `is_hidden` state.
- On change:
  - Optimistically disable the control, send PATCH.
  - On success: if hiding, remove node from Cytoscape and clear Task Panel selection; if unhiding (when visible), keep selection; if recovery view is active, keep element in place but update style.
  - On error: revert toggle and show toast/error.
- Optional for recovery (recommended): a header-level toggle “Show hidden” to fetch with `include_hidden=1` and render hidden nodes with low opacity and dashed border; this allows re-selecting and unhiding. If not implemented now, provide a CLI/admin fallback.

4.4 Styling
- Hidden (in recovery mode): low opacity, dashed border, disabled pointer events except selection; tooltip “Hidden”.

4.5 Groups Policy (MVP)
- Hiding a group hides the group node itself. Children remain unaffected/visible. Rationale: keeps model simple and avoids accidental loss of large subgraphs from view. We can add recursive policies later.

### 5) Implementation Plan (Step-by-Step)

Backend
1. Migration: create Alembic revision `add_is_hidden_to_node`.
   - Add column `is_hidden` to table `node`, Boolean, nullable=False, server_default=false.
   - Backfill existing rows to false if needed, then drop server_default if project standard requires.
2. Model: update `app/models/__init__.py` `Node` to include `is_hidden: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False)`.
3. Schema: update `NodeSchema` to add `is_hidden = fields.Boolean()`.
4. API: update `list_nodes` in `app/blueprints/graph/routes.py` to filter hidden by default; parse `include_hidden` query to override behavior.
5. API: no change needed for edges; ensure client gracefully handles missing endpoints.

Frontend
6. Load: Adjust `toElements` mapping in `app/templates/project.html` to include `is_hidden` in `data` for nodes (when present).
7. Task Panel UI: add the checkbox “Hide from board”. Wire it to selected node state.
8. Actions: on toggle → `PATCH /api/v1/nodes/{id}` with `{ is_hidden }`. On success:
   - If hiding in normal mode: remove element and clear Task Panel selection.
   - If recovery mode on: keep element but apply hidden styling.
9. Optional Recovery: add a header toggle “Show hidden” that refetches with `include_hidden=1` and updates Cytoscape elements; style hidden nodes distinctly; allow selecting and unhiding.
10. Persist minor UX states in `localStorage` (e.g., recovery toggle), consistent with existing language and sidebar states.

Testing
11. Unit tests (if present): extend service/repository tests to verify `is_hidden` default and filtering behavior.
12. API tests: verify PATCH toggling and list filtering; verify `include_hidden` behavior.
13. Manual tests: see section below.

Rollout
14. Backward compatibility check; ensure no client crashes when `is_hidden` absent (older DB) — guarded by migration ordering.
15. Update docs and changelog in this roadmap.

### 6) Manual Testing Checklist (UI Click-Through)

Preparation
- Open the app, create or open an existing board.

Happy Path
- Create a new node → it appears on the board.
- Select the node → in Task Panel, toggle “Hide from board” on.
- Observe: node disappears from the board immediately; Task Panel selection clears.
- Refresh the page → node remains hidden (not present in the board graph).

Unhide (if recovery mode implemented)
- Turn on “Show hidden” in the page header.
- Verify hidden nodes appear faded/dashed.
- Select a hidden node → toggle off “Hide from board”.
- Verify: node becomes normal; turn off “Show hidden”, node remains visible.

Edge Cases
- Hide a node that has multiple incoming/outgoing edges → no JS errors; edges with missing endpoints are ignored.
- Hide a group node (MVP policy): only the group node disappears; children remain visible.
- Toggle rapidly on/off → server updates are debounced or handled sequentially without race conditions; final state matches last toggle.

### 7) Risks and Mitigations

- Discoverability of unhide: Without recovery view, users cannot unhide. Mitigation: add optional global “Show hidden” toggle; document fallback via API.
- Data skew during concurrent edits: Use last-write-wins; UI disables control while request is in-flight; re-fetch on resume if needed.
- Large graphs: Additional filtering is trivial; ensure no extra N+1 queries are introduced.

### 8) API Contract Examples

PATCH /api/v1/nodes/{id}
Request:
```json
{ "is_hidden": true }
```
Response (200):
```json
{ "data": { "id": "...", "title": "...", "is_hidden": true, "status": "planned", "priority": "normal", "created_at": "..." } }
```

GET /api/v1/projects/{project_id}/nodes (default)
```text
Excludes nodes with is_hidden = true
```

GET /api/v1/projects/{project_id}/nodes?include_hidden=1
```text
Includes both hidden and visible nodes; each item has is_hidden flag
```

### 9) Acceptance Criteria (Checklist)

- [ ] Migration adds `is_hidden` to `node` with default false.
- [ ] Model updated; schema updated.
- [ ] `GET /projects/{id}/nodes` excludes hidden by default.
- [ ] `PATCH /nodes/{id}` supports toggling `is_hidden`.
- [ ] Task Panel toggle implemented; hides immediately on success.
- [ ] Optional: “Show hidden” global toggle and hidden styling.
- [ ] Manual test cases pass.

### 10) Changelog (Work Log)

- [ ] 2025-08-31 — Roadmap drafted and awaiting approval.
- [ ] TBD — Migration implemented.
- [ ] TBD — API and UI implemented.
- [ ] TBD — Tests added/updated, manual verification done.

### 11) Open Questions

- Should we include the recovery UI (“Show hidden”) in this iteration? Otherwise, unhiding requires API/CLI.
- For group nodes, do we want an option to hide descendants recursively in a future iteration?


