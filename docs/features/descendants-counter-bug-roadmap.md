# Descendants Counter Bug – Roadmap

Created: 2025-09-13 (UTC)

## Context
The sidebar's task panel field "Descendants (via edges)" used to display a non-zero value for nodes with reachable descendants. Recently it always shows 0, while node dot sizes on the board still react to descendants-based logic. We need to analyze, fix, and document this issue.

## Initial Prompt (translated from Russian)
"There is a task panel in the sidebar, and it has Descendants (via edges). It stopped displaying correctly, although it used to. Now it's always 0, although the node dot size increases on the board. Fix it.

=== Analyse the Task and project ===
Deeply analyze our task, our project, and decide how best to implement it.

=== Create Roadmap ===
Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in as much detail as possible all identified and tried problems, nuances, and solutions, if any. As you progress in implementing this task, you will use this file as a to-do checklist, updating this file and documenting what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and comment. If during the implementation it becomes clear that something needs to be added from tasks—add it to this document. This will help us maintain the context window, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project captions.
When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt you wrote in the plan, but translate it into English. You can name it in the document-plan something like "Initial Prompt". This is necessary to preserve the context of the task statement in our roadmap file as accurately as possible without any "broken telephone" effect.

Also include steps for manual testing, that is, what needs to be clicked in the interface."

## Discovery and Current Behavior
- Frontend template: `app/templates/project.html`
  - The field is rendered twice (both with `id="descCount"`).
    - Metadata block:
      - Label: Descendants (via edges)
      - Value element: `<div id="descCount">`
    - Visibility & Metrics block:
      - Label: Descendants (via edges)
      - Value element: `<div id="descCount">`
  - Node selection handler (`cy.on('tap', 'node', ...)`) computes descendants via BFS using `outgoers('edge')` and then sets: `document.getElementById('descCount').textContent = String(count);`
  - Elements conversion also computes `n.data.descendants` client-side for LOD and sizing.
- Backend edges API: `GET /api/v1/projects/<project_id>/edges` implemented in `app/blueprints/graph/routes.py` returns all edges for the project.

## Root Cause Hypothesis
- Duplicate IDs in DOM: there are two elements with `id="descCount"`. `document.getElementById` returns the first matching element only. Depending on the current DOM order or layout reordering, we may be updating the hidden/non-visible block, leaving the visible block unchanged, making it look like the value is always 0.
- This aligns with the observation: descendant size on the board still changes (client-side descendants computation is intact), but the sidebar display does not update as expected.

## Fix Strategy (KISS, DRY, SoC)
1. Replace duplicate `id` with unique identifiers and update bindings:
   - Rename the fields to `descCountMeta` and `descCountVisibility` (or consolidate to a single source of truth if only one should be visible at a time).
   - Create a small helper `updateDescendantsCount(count)` that updates all relevant UI targets.
   - Replace direct `getElementById('descCount')` usage with the helper.
2. Ensure updates happen on:
   - Node tap/select.
   - Edge add/delete events (already recompute descendants for sizes; extend to update the UI helper once per operation).
   - Graph reload / initial selection.
3. Keep computation single-sourced:
   - Reuse the BFS computation already present on node tap.
   - Optionally extract BFS into a function `computeDescendantsCount(startNodeId)` to avoid duplication.

## Detailed Steps
- HTML edits in `app/templates/project.html`:
  - Change both occurrences of `<div id="descCount" ...>` to unique ids: `<div id="descCountMeta">` and `<div id="descCountVis">`.
- JS edits in the same template:
  - Add function `updateDescendantsCount(count)` that writes into both elements if present.
  - Replace `const dc = document.getElementById('descCount'); if (dc) dc.textContent = String(count);` with `updateDescendantsCount(count)` in node tap handler.
  - In `addEdgeToCy` after recomputation of `descendants`, update current selection count (if a node is selected) via the same helper.
  - Similarly, on edge delete flows (where applicable), refresh the count.
  - Optionally extract BFS into `computeDescendantsCount(selectedNodeId)` used in all spots.

## Acceptance Criteria
- Selecting a node with k reachable descendants updates both sidebar locations consistently to k.
- Adding/removing edges that change reachability updates the count for the currently selected node without requiring a full page reload.
- No duplicate ids remain in the template.
- No console errors/linter issues introduced.

## Manual Test Plan
1. Open a project page.
2. Select a node that has outgoing edges forming multiple levels of descendants.
   - Expected: both Descendants counters show the same non-zero value.
3. Select a leaf node (no outgoing edges).
   - Expected: both counters show 0.
4. Add an edge from the previously selected node to a new target.
   - Expected: count increments accordingly for the selected node.
5. Delete the added edge.
   - Expected: count decrements accordingly.
6. Toggle visibility blocks (collapse/expand) and reorder sidebar blocks if the UI supports it.
   - Expected: counters continue to display correct values.
7. Reload the page and re-select the same node.
   - Expected: counters compute and display correctly again.

## Risks and Mitigations
- Risk: There may be other code paths updating `descCount` by id. Mitigation: consolidate to helper method and search/replace all references.
- Risk: Performance of BFS on very large graphs. Mitigation: The existing approach is already used; scope remains unchanged.

## Work Items and Status
- [ ] Update template IDs to unique names.
- [ ] Add `updateDescendantsCount(count)` helper.
- [ ] Replace direct updates with the helper in node tap handler.
- [ ] Update `addEdgeToCy` and edge delete logic to call the helper when a node is selected.
- [ ] Retest manually per plan.
- [ ] Document outcomes here.

## Notes
- Code and in-app texts remain in English per project rules.
