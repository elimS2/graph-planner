## Graph Auto-Layout Preview — Roadmap

### Status
- Owner: Core
- Created: 2025-09-14
- State: Draft

---

### 1) Initial Prompt (translated to English)

We have a board where points (nodes) are displayed. I place them on the board and their coordinates are saved. But it’s not always possible to place them successfully. Sometimes they overlap each other or their connections (edges) cross.

I became interested in whether there is any algorithmic approach to automatically arrange them on the board. I’d like to add a button that shows how they could be optimally placed, but without overwriting my coordinates (i.e., how I placed these points). It should just show, for example, in some view switch, and that’s it, without saving the coordinates.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document all discovered and tried issues, nuances, and solutions as much as possible if any exist. As you progress with the implementation of this task, you will use this file as a to-do checklist, update this file, and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items; you can only update their status and comment. If during implementation it becomes clear that something needs to be added from the tasks — add it to this document. This will help us preserve context, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in the code and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design
Use Best Practices

==================================================

=== Get time from MCP Server ===

If you need the current time, get it from the time MCP Server.

---

### 2) Context and Current Behavior

- Frontend: `app/templates/project.html` renders the graph via Cytoscape. Elements are created in `toElements(graph)`. Node saved positions are attached as `data.savedX`, `data.savedY`.
- Initial positioning: `applyInitialPositions()` restores saved positions for nodes with saved coordinates, and runs `cose` layout only for nodes without saved coordinates.
- Persistence: On user drag end (`cy.on('dragfree','node', ...)`), the current position is sent to the backend `POST /api/v1/nodes/<id>/position` and saved in `node_layout` table.
- Backend: `app/blueprints/graph/routes.py`
  - `GET /projects/<project_id>/nodes` includes `position` from `NodeLayout` when present.
  - `POST /nodes/<node_id>/position` upserts a `NodeLayout` record.
- There is no explicit “layout preview” mode — layouts are either applied at init (for missing positions) or the user manually drags nodes.

Implication: Users can end up with overlapping nodes and crossing edges. We want an on-demand preview of an auto-layout that does not persist to the database and can be toggled off to restore saved/manual positions.

---

### 3) Goals and Non-Goals

- Goals
  - Provide a non-destructive “Suggested Layout” preview mode that temporarily repositions nodes using a selected algorithm.
  - Add a UI toggle to switch between Saved layout (user coordinates) and Suggested layout (algorithmic). No DB writes in preview mode.
  - Allow choosing an algorithm best suited for the graph structure (e.g., DAG-like vs general graph) and tune options.
  - Clearly indicate preview mode and provide a one-click restore to saved positions.

- Non-Goals (for this iteration)
  - Automatic persistence of suggested layout to DB.
  - Server-side layout computation.
  - Complex edge-crossing optimization beyond what established layout algorithms provide.

---

### 4) Algorithm Options and Rationale

- Force-directed (good general-purpose, overlap reduction):
  - `fcose` (Cytoscape extension): scalable, overlap-minimization, good aesthetics.
  - Built-in `cose` (already used) is simpler but produces more crossings/overlaps on large graphs.
- Layered DAG layout (reduces crossings when the graph is acyclic or mostly directional):
  - `dagre` (Cytoscape extension): rank-based, minimizes edge crossings; good for task flows.
- Concentric / Grid:
  - Built-in `concentric` or `grid` as quick, deterministic fallbacks.

Proposed default: `fcose` for general graphs with a “Graph Type” hint to try `dagre` when edges mostly point forward (optional heuristic).

---

### 5) UX Design

- Toolbar additions (English labels per project guidelines):
  - Toggle: `Layout: Saved | Suggested`
  - When `Suggested` is active:
    - Dropdown: `Algorithm: fcose | dagre | cose | concentric | grid`
    - Button: `Run`
    - Note/badge: `Preview mode — positions are not saved`
  - Button: `Restore Saved` (always enabled; re-applies saved coordinates)
- Behavior:
  - Switching to `Suggested` runs the chosen layout on current Cytoscape instance.
  - While in preview, dragging nodes should not persist positions. A guard flag disables POSTing in `dragfree` handler.
  - Switching back to `Saved` restores node positions from `data.savedX/savedY` for nodes that have them. For nodes without saved positions, use a snapshot taken immediately before the preview started.
- Visual feedback:
  - Show a subtle banner/pill in the canvas corner when preview is active.
  - Consider dimming the “Save/Apply” controls (there are none for this iteration) to prevent confusion.

---

### 6) Technical Design

- Frontend only; no backend changes required.
- Include required layout extensions in `project.html` via CDN:
  - `cytoscape-fcose`
  - `cytoscape-dagre` (+ `dagre` dependency)
- New state flags and helpers in `project.html` script:
  - `let layoutPreviewActive = false;`
  - `let savedPositionSnapshot = new Map<string, {x:number, y:number}>();` (positions right before entering preview)
  - `function captureCurrentPositions(): void`
  - `function restoreSavedPositions(): void` (prefers `data.savedX/Y` if both are numeric; otherwise snapshot)
  - `async function runSuggestedLayout(algo: 'fcose' | 'dagre' | 'cose' | 'concentric' | 'grid', opts?: object): Promise<void>`
  - Guard in existing `dragfree` handler: `if (!layoutPreviewActive) { persist }`
- Heuristic (optional, later): detect DAG-ness (check for cycles or density of back-edges) to recommend `dagre`.

Performance & safety:
- For large graphs, use `animate: false`, reasonable `quality`, and limit iterations for `fcose`.
- Run on visible nodes (exclude hidden) to keep it responsive.
- Ensure restoration does not cause drift: always set absolute positions.

---

### 7) Implementation Plan (Step-by-Step)

1) Prepare libraries
   - Add `<script>` tags for `dagre`, `cytoscape-dagre`, and `cytoscape-fcose` in `project.html` after Cytoscape load.

2) UI controls
   - Add toolbar toggle `Layout: Saved | Suggested` and dropdown `Algorithm` + `Run` button.
   - Add a small banner/pill to indicate preview mode and a `Restore Saved` button.

3) State and wiring
   - Introduce `layoutPreviewActive` flag and `savedPositionSnapshot`.
   - Wire toggle: on switch to `Suggested`, call `captureCurrentPositions()` then `runSuggestedLayout()` with selected algorithm.
   - On switch to `Saved`, call `restoreSavedPositions()`; set `layoutPreviewActive = false`.

4) Persistence guard
   - Update existing `dragfree` handler to early-return if `layoutPreviewActive` is true (do not POST positions).

5) Restore logic
   - Implement `restoreSavedPositions()` to iterate all nodes:
     - If both `data('savedX')` and `data('savedY')` are numbers, set position to those.
     - Else, fall back to `savedPositionSnapshot`.
   - Fit/keep viewport stable (optional): keep current pan/zoom unchanged.

6) Suggested layout runner
   - Map algorithm name to Cytoscape layout configs with sane defaults:
     - fcose: `{ name: 'fcose', quality: 'default', nodeRepulsion: 4500, idealEdgeLength: 120, animate: false }`
     - dagre: `{ name: 'dagre', rankDir: 'LR', nodeSep: 30, rankSep: 60, edgeSep: 10 }`
     - cose: `{ name: 'cose', animate: false }`
     - concentric/grid: built-in defaults
   - Exclude hidden nodes from layout if practical, or run on the whole graph (start simple).

7) QA and polish
   - Verify no DB writes occur during preview.
   - Confirm drag in preview does not persist.
   - Confirm restoring saved positions is exact.
   - Add minimal error handling and toasts if layout extension failed to load.

8) Documentation & toggles
   - Document in this roadmap.
   - Add a feature flag constant (optional) for easy disable.

---

### 8) Manual Testing Checklist

Basic flow
1. Open a project with several nodes and edges.
2. Ensure some nodes have saved positions (drag a few; confirm they persist after refresh).
3. Click `Layout: Suggested`.
4. Select `Algorithm: fcose` and click `Run`.
5. Observe nodes rearranged; ensure no network requests saving positions were made.
6. Drag a node while in preview and release. Confirm no position POST occurs and refreshing the page returns to the previously saved layout.
7. Click `Restore Saved`. Confirm layout exactly restores to saved coordinates.

Algorithm switching
8. While still in `Suggested`, change to `Algorithm: dagre` and `Run`. Confirm layout changes accordingly.
9. Switch back to `Saved`. Confirm restoration is correct.

Edge/crossing checks
10. Compare overlaps/crossings between `fcose` and `dagre` on a DAG-like subset.

Hidden nodes
11. Hide a few nodes (if feature exists). Run `Suggested` again. Confirm behavior is acceptable (either included or excluded consistently).

Stress
12. Try with 100–300 nodes. Confirm UI remains responsive; `Run` completes; restoration works.

---

### 9) Risks, Constraints, Mitigations

- Extensions not loading (CSP, CDN):
  - Mitigation: Fallback to built-in `cose` and show a non-intrusive toast.
- Large graphs slow layout:
  - Mitigation: lower quality, disable animation, consider limiting to visible nodes.
- Users think preview saved:
  - Mitigation: prominent "Preview mode — positions are not saved" label; require explicit save button (not in this iteration).
- Mixed saved/unsaved nodes:
  - Mitigation: snapshot before preview; restoration prefers saved coordinates when available.

---

### 10) Acceptance Criteria

- A user can toggle between `Saved` and `Suggested` layouts without any changes being persisted to the backend.
- Dragging nodes during preview does not save positions.
- Restoration returns nodes to their saved coordinates, exactly for nodes that have them; others return to the snapshot taken before preview.
- At least two algorithms are available (`fcose`, `dagre`) plus basic fallbacks.
- No regressions to initial load positioning or position persistence outside preview mode.

---

### 11) Future Enhancements (Backlog)

- Add an optional "Apply Suggested Layout" action to persist the preview to DB (with confirmation).
- Server-side batch layout for consistency and reproducibility.
- Heuristic to auto-pick `dagre` for DAG-heavy graphs.
- Collision-avoidance post-processing pass to reduce residual overlaps.
- Per-group or subgraph layouting.

---

### 12) Work Log / Checklist

- [x] Add `dagre`, `cytoscape-dagre`, `cytoscape-fcose` scripts to `project.html`.
- [x] Add toolbar toggle and algorithm selector.
- [x] Implement preview state, snapshot capture, and restoration.
- [x] Guard `dragfree` persistence during preview.
- [x] Implement `runSuggestedLayout` with configs for algorithms.
- [ ] Manual QA per checklist.
- [ ] Document and finalize.


