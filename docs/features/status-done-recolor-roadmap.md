## Immediate Edge Recolor on "Done" Status — Roadmap and Design

### Initial Prompt (translated)

If we change a point's priority, the graphs are recalculated immediately without reloading the page.

But if for a point with high or critical priority we mark the status as done, then the graph color resets only after reloading the page. We need it to reset immediately as well.

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
- Edge coloring has two parallel mechanisms:
  - Path-based highlighting via edge data `pathPriority` computed by `recomputePriorityPaths()` using downstream highest priority among nodes that are not done.
  - Direct target-based styling via Cytoscape selectors using edge data `targetPriority` and `targetStatus` (e.g., `edge[targetPriority="critical"][targetStatus != "done"]`).
- On page load, edges are created with both fields via the initial `toElements` mapping.
- On runtime changes:
  - When priority is changed: node `data('priority')` is updated, and `recomputePriorityPaths()` is called.
  - When status is changed: node `data('status')` is updated, and `recomputePriorityPaths()` is called.
  - However, edge data attributes for direct selectors are not updated:
    - `targetStatus` on edges pointing to the node is not refreshed after a status change.
    - `targetPriority` on edges pointing to the node is not refreshed after a priority change.
  - In addition, `addEdgeToCy(...)` sets `targetPriority` but not `targetStatus`, so newly added edges may miss the direct-status styling.

Implication: Even though `recomputePriorityPaths()` clears `pathPriority`, the direct target-based selectors may still apply due to stale `targetStatus`/`targetPriority` values on edges, causing colors to persist until a full reload.

### 2) Root Cause

Stale edge-level flags `targetStatus` and `targetPriority` are not synchronized when a node's status or priority changes. Cytoscape style precedence allows later direct selectors to keep the edge colored even if `pathPriority` has been reset.

### 3) Goals and Non-Goals

Goals:
- Ensure edges immediately lose high/critical coloring when a high/critical target node is set to `done`, without a page reload.
- Keep priority-change behavior instant as-is.
- Keep the UI code clean and DRY.

Non-Goals (for this task):
- Backend changes. The current API is sufficient; this is a client-side state sync issue.
- Altering the semantic of path-based highlighting.

### 4) Design Decisions

4.1 Synchronize edge target flags on node updates
- On node status change: update `targetStatus` on all incoming edges to that node.
- On node priority change: update `targetPriority` on all incoming edges to that node.
- Then call `recomputePriorityPaths()` (already present) to keep path-based highlighting consistent.

4.2 DRY helper function
- Add a small helper: `refreshEdgeTargetFlags(nodeId)` that:
  - Reads the node's current `data('status')` and `data('priority')`.
  - Iterates `cy.edges(`[target = "${nodeId}"]`)` and sets `e.data('targetStatus', status)` and `e.data('targetPriority', priority)`.
  - Is called after successful responses of both the Status and Priority radio handlers.

4.3 Fix for dynamic edge creation
- In `addEdgeToCy(e)`, also set `targetStatus` from the target node's current data, not only `targetPriority`.

4.4 Optional simplification (deferred)
- Consider removing direct target-based selectors and rely purely on `pathPriority`. For now, keep both mechanisms and ensure synchronization for minimal risk and consistent UX.

### 5) Implementation Plan (Step-by-Step)

Frontend (`app/templates/project.html`):
1. Introduce `refreshEdgeTargetFlags(nodeId)` helper.
2. In Status radio handler (after `n.data('status', ...)`): call `refreshEdgeTargetFlags(selectedNodeId)` before `recomputePriorityPaths()`.
3. In Priority radio handler (after `n.data('priority', ...)`): call `refreshEdgeTargetFlags(selectedNodeId)` before/after `recomputePriorityPaths()`.
4. Update `addEdgeToCy(e)` to also set `targetStatus` from the actual target node.
5. Verify there are no other code paths that mutate node status/priority without invoking the helper. If any, wire the helper there as well.

Testing and Validation:
6. Manually test scenarios below across different browsers.
7. Optionally add a lightweight UI test snippet to verify edge data mutation behavior in dev tools.

Docs/Changelog:
8. Update this roadmap's Work Log as steps are completed.

### 6) Manual Testing Checklist (UI Click-Through)

Preparation
- Open a project with at least two nodes A and B, and an edge A → B.
- Set B priority to `high` or `critical`.

Happy Path
- Select B; change status to `done`.
- Observe immediately: all incoming edges to B drop red/orange coloring and revert to default gray. No page reload.
- Change status back to `planned` or `in-progress` and confirm edges re-apply coloring as expected.

Priority Path Validation
- With B status not `done`, change its priority between `normal` → `high` → `critical` and verify edge coloring updates instantly.
- Mark B as `done` again; verify coloring resets instantly.

Dynamic Edge Case
- With B currently `done`, create a new edge A2 → B.
- Verify the new edge is gray (not colored), confirming `targetStatus` is applied on creation.

Regression Checks
- `recomputePriorityPaths()` still produces correct `pathPriority` overlays for complex graphs.
- Status/priority changes for non-target nodes do not cause unexpected edge recoloring.

### 7) Risks and Mitigations

- Style precedence: Ensure direct selectors do not override `pathPriority` incorrectly when `targetStatus` is up-to-date. Mitigated by synchronizing flags and keeping selector order unchanged.
- Performance: Updating incoming edges for a node is O(in-degree) and fast for typical graphs. No measurable impact expected.
- Consistency: Ensure helper is called in all relevant mutation paths; centralizing in radio handlers and edge creation covers current flows.

### 8) Acceptance Criteria (Checklist)

- [ ] Changing a node with `high`/`critical` priority to `done` immediately removes edge coloring without page reload.
- [ ] Changing priority still recolors instantly, with no stale states.
- [ ] Newly created edges correctly initialize both `targetPriority` and `targetStatus`.
- [ ] No backend changes required; no console errors; performance unaffected.

### 9) Changelog (Work Log)

- [ ] 2025-08-31 — Roadmap drafted, awaiting approval.
- [ ] TBD — Implement helper and wire to status/priority handlers.
- [ ] TBD — Update `addEdgeToCy` to set `targetStatus`.
- [ ] TBD — Manual verification completed.

### 10) Open Questions

- Do we want to eventually remove the direct target-based selectors and rely purely on `pathPriority` to simplify styling rules?


