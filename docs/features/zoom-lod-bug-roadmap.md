## Zoom/LOD Bug – Roadmap and Implementation Plan

### Context and Symptoms
- The board uses Cytoscape.js for rendering (`app/templates/project.html`).
- When zooming out after recently interacting with a node (add/edit/select), almost all nodes disappear and only the last interacted node remains visible.
- After a full page reload, zooming out behaves correctly: the entire board scales smoothly, nodes do not disappear.

### Initial Prompt (verbatim in English)
The user’s original task description translated to English and preserved for context.

"""
There is a zoom bug: if you decrease the scale on the board (i.e., zoom out so that the dots on the board become smaller), then only the last dot remains — the one you last worked with, for example added or edited. After reloading the page, when zooming out, all dots do not disappear except one; the entire board smoothly scales instead.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan to implement this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in this file all the identified and tried problems, nuances, and solutions as much as possible, if any exist. As you progress with the implementation of this task, you will use this file as a to-do checklist; you will update this file and document what has been done, how it was done, what problems arose, and what solutions were adopted. For history, do not delete items; you can only update their status and comment. If, during implementation, it becomes clear that something needs to be added from tasks — add it to this document. This will help us keep context, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in code and comments, labels of the project. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt that I wrote to you into the plan, but translate it into English. You can call this in the plan document something like "Initial Prompt". This is necessary to preserve the context of the task-setting in our roadmap file as accurately as possible without the "broken telephone" effect.

Also include steps for manual testing, i.e., what needs to be clicked through in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.
"""

### Current Implementation Snapshot
- Zoom controls: custom smooth zoom, wheel handling, and disabled default user zoom.
- LOD (Level of Detail) logic listens to Cytoscape `zoom` and toggles node visibility.
- Relevant areas in `app/templates/project.html`:

```1398:1452:app/templates/project.html
        // Zoom controls with smooth animation
        function smoothZoom(factor){
          const target = cy.zoom() * factor;
          cy.animate({ zoom: target }, { duration: 200, easing: 'ease-in-out' });
        }
        document.getElementById('zoomIn').addEventListener('click', () => smoothZoom(1.2));
        document.getElementById('zoomOut').addEventListener('click', () => smoothZoom(1/1.2));
        // smoother wheel zoom (RAF-based, responsive, anchored to cursor)
        cy.userZoomingEnabled(false);
        const cyContainer = cy.container();
        let targetZoom = cy.zoom();
        let anchor = { x: 0, y: 0 };
        let zooming = false;
        function stepZoom(){
          if (!zooming) return;
          const current = cy.zoom();
          const next = current + (targetZoom - current) * 0.25; // responsiveness factor
          cy.zoom({ level: next, renderedPosition: anchor });
          if (Math.abs(targetZoom - next) < 0.001) { zooming = false; return; }
          requestAnimationFrame(stepZoom);
        }
        cyContainer.addEventListener('wheel', (e) => {
          e.preventDefault();
          const rect = cyContainer.getBoundingClientRect();
          anchor = { x: e.clientX - rect.left, y: e.clientY - rect.top };
          const factor = Math.exp(-e.deltaY * 0.0012); // slightly faster response
          targetZoom = Math.max(0.05, Math.min(10, targetZoom * factor));
          if (!zooming) { zooming = true; requestAnimationFrame(stepZoom); }
        }, { passive: false });
```

```1097:1127:app/templates/project.html
        // LOD: hide nodes below threshold depending on zoom level
        function applyLOD() {
          const z = cy.zoom();
          const total = cy.nodes().length;
          // Only hide at low zoom for sufficiently large graphs
          let threshold = -1;
          if (total > 100) {
            if (z < 0.4) threshold = 1.5;
            else if (z < 0.8) threshold = 0.6;
            else threshold = -1;
          }

          let shown = 0;
          cy.nodes().forEach(n => {
            const score = n.data('score') || 0;
            const isSelected = selectedNodeId && n.id() === selectedNodeId;
            const isCollapsedChild = Boolean(n.data('origParent'));
            const visible = !isCollapsedChild && (threshold < 0 || score >= threshold || isSelected);
            n.style('display', visible ? 'element' : 'none');
            if (visible) shown++;
          });

          // Safety: if nothing would be visible, show all
          if (shown === 0) {
            cy.nodes().forEach(n => {
              if (!n.data('origParent')) n.style('display', 'element');
            });
          }
        }
        cy.on('zoom', applyLOD);
        applyLOD();
```

### Root Cause Analysis
- `applyLOD` decides visibility using `score` read from `n.data('score')`. In current graph data, most nodes do not have `score` set, so it defaults to `0`.
- When zoomed out and `threshold` becomes `>= 0`, all nodes with `score < threshold` are hidden. Due to the `isSelected` override, the last interacted node remains visible.
- The safety guard only restores visibility when `shown === 0`, but because the selected node is still visible (`shown === 1`), the guard does not trigger. This matches the observed behavior: only one node remains visible until a refresh (which clears selection), after which `shown` becomes `0` and the guard restores visibility.

### Design Goals
- Preserve performance for very large graphs.
- Avoid pathological cases where only 0–1 nodes remain visible when zooming.
- Keep the interaction model intuitive and predictable.
- Keep the code simple (KISS) and maintainable (SOLID/DRY/SoC).

### Proposed Solution
1. Replace reliance on missing `data('score')`:
   - Compute a stable `lod_score` for each node at build time in `toElements` using a simple, cheap metric:
     - `lod_score = 0.6 * normalizedDegree + 0.4 * normalizedDescendants`.
     - Fallback if data missing: use `degree()` and `descendants` already computed.
   - Store as `data('lod_score')` to avoid conflict with future semantics of `score`.
2. Adjust LOD thresholds and safeguards:
   - Disable LOD entirely for `total <= 150`.
   - Use thresholds that scale with zoom but guarantee a minimum number of visible nodes:
     - Define `minVisible = Math.min(80, Math.ceil(total * 0.2))`.
     - If the first pass yields fewer than `minVisible`, iteratively relax the threshold until the minimum is met.
   - Keep `selected` nodes visible, but base the safety guard on the count excluding the selected node, to avoid the 1-node trap.
3. Prefer opacity reduction over `display: none` for medium zoom ranges, and switch to `display: none` only at very low zoom and very large graphs. This keeps spatial context while still improving performance.
4. Add a user toggle to enable/disable LOD in the UI (persisted in `localStorage`) for debugging and accessibility.
5. Ensure LOD re-applies consistently after graph reload/layout, sidebar resize, language changes, or filter changes.

### Acceptance Criteria
- Zooming out never results in only the last interacted node being visible.
- For graphs with ≤ 150 nodes, all nodes remain visible during zoom; only label/icon sizes change.
- For large graphs, a meaningful subset remains visible when zoomed out, but never fewer than `minVisible`.
- Selection does not mask the LOD safety guard.
- A UI toggle exists to disable LOD, persisted across sessions.

### Implementation Steps (Checklist)
1. Compute `lod_score` in `toElements` using degree/descendants; attach to node `data`. [DONE]
2. Refactor `applyLOD` to use `lod_score` with zoom-aware thresholds and `minVisible` backoff. [DONE]
3. Change visibility strategy:
   - Medium zoom: reduce `opacity` (e.g., 0.25) instead of hiding.
   - Low zoom and very large graphs: hide (`display: none`) least important nodes first.
4. Update safety guard to consider visibility excluding the selected node; if below `minVisible`, relax threshold and re-apply.
5. Add a UI toggle "Performance LOD" with persistence; when off, all nodes remain visible and only style tweaks apply. [DONE]
6. Re-apply LOD after: layout run, fit, language reload, filter/search change, sidebar toggle/resize. [DONE]
7. Add inline comments (English) with rationale and guardrails.
8. Manual test pass across scenarios (see below).

### Progress Log
- [DONE] Compute `lod_score` for each node in `toElements` combining normalized degree and descendants. No linter issues.
- [DONE] Refactor `applyLOD` to use `lod_score`, add minVisible guard, mid-zoom opacity fade, low-zoom hiding, and ranked selection to avoid the single-selected-node trap. No linter issues.
- [DONE] Add "Performance LOD" toggle in Settings sidebar; persisted in localStorage; `applyLOD` respects it.
- [DONE] Audit hooks to re-apply LOD after layout, reload, filter, and resize. Added calls after language reload, grouping changes, ungroup, group creation, and sidebar resize/toggle.

### Timestamps
- lod_score implementation completed at: 2025-08-31T21:21:13Z (UTC)
- applyLOD refactor completed at: 2025-08-31T21:22:56Z (UTC)
- LOD UI toggle completed at: 2025-08-31T21:26:36Z (UTC)
- Re-apply hooks audit completed at: 2025-08-31T21:30:54Z (UTC)

### Manual Testing Scenarios
- Basic zoom behavior
  - Open a project with ~50 nodes. Zoom in/out via buttons and mouse wheel. Verify no nodes disappear.
  - Interact with a node (add/edit/select), then zoom out. Verify no single-node-only state.
- Large graph behavior
  - With a project > 200 nodes, zoom out. Verify at least `minVisible` nodes remain, and reduce smoothly as zoom decreases. Selected node stays visible but not alone.
  - Toggle "Performance LOD" off and repeat. Verify all nodes remain visible.
- Interaction consistency
  - After language change and graph reload, zoom out: LOD still correct.
  - After filtering by status or search query, zoom behavior remains consistent.
  - After sidebar toggle/resize, `cy.resize()` happens and LOD re-applies.
- Edge cases
  - Collapsed groups: children remain hidden; group parents follow LOD rules.
  - Zero-degree nodes: still included in `lod_score` normalization; not all get hidden.
  - Selection cleared: safety still prevents near-empty visibility.

### Risks and Mitigations
- Performance: opacity vs display may reduce gains. Mitigation: only use opacity for mid-zoom and switch to display at lowest zoom on big graphs.
- Scoring correctness: simple degree/descendants metric may be imperfect. Mitigation: threshold backoff ensures minimum visibility regardless of score skew.
- User confusion: LOD may hide nodes unexpectedly. Mitigation: add visible toggle and tooltip explaining behavior.

### Rollback Plan
- Keep changes isolated to `project.html` front-end logic. If issues arise, toggle LOD off by default or revert to pre-change LOD quickly.

### Time Estimate
- Analysis and design: 1–2 hours
- Implementation: 2–4 hours
- Manual testing and refinements: 1–2 hours

### Revision Log
- [Planned] v1: Introduce `lod_score`, threshold backoff, min visible safeguard, UI toggle.
- [Future] v2: Consider CSS-based label visibility tuning and Cytoscape stylesheet optimizations.


