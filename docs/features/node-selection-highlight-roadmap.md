Title: Node Selection Highlight – Roadmap
Timestamp (UTC): 2025-09-11T19:54:09.099685+00:00

1. Context and Goal
- We need to visually highlight a clicked/selected node on the board so that it stands out among others, following good UI/UX practices.

2. Initial Prompt (English)
"I want to somehow highlight on the board the selected point, the one that was clicked. So that it stands out relative to other points. I don’t know how to do this correctly, how it is accepted in designs and best UX/UI practices.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in the file as much as possible all problems, nuances and solutions already discovered and tried, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks – add it to this document. This will help us keep the context window, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, the inscriptions of the project. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing in the plan, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design
Use Best Practices

==================================================

=== Get time from MCP Server ===

If you need the current time. Get it from the time MCP Server"

3. Current Implementation Analysis (Project)
- Graph library: Cytoscape.js (app/templates/project.html includes cytoscape 3.28.1).
- Selection flows found:
  - Node tap handler sets `selectedNodeId` and updates side panel; edges have separate selection (`selectedEdgeId`).
  - Cytoscape default selection styling exists for edges via `edge:selected`.
  - No explicit `node:selected` style is defined yet; nodes use color by status and additional classes (`.cp`, `collapsed`, `?is_group`).
  - Data-driven styles: `status`, `priority`, `is_hidden`, `descendants`; edges reflect target node flags.
- LOD and visibility logic hides elements at zoom levels; must ensure selected node remains visible.
- Sidebar auto-hide and reveal on node tap; should coordinate with highlight.

4. Proposed UX Design (Best Practices)
- Visual focus ring: add a clear, accessible highlight ring around the selected node.
  - Use `node:selected` style with thicker border and glow (outline) distinct from status color.
  - Maintain WCAG contrast; avoid relying on color only: thickness + subtle shadow.
- De-emphasis of non-selected elements (optional, toggleable):
  - On selection, slightly reduce opacity of non-selected nodes and edges to draw focus.
  - Keep performance by using classes rather than per-element inline styles.
- Maintain visibility and context:
  - Ensure selected node is revealed (not hidden by LOD) and brought into view with small animated pan/zoom.
- Keyboard accessibility:
  - Support selecting the currently focused node via keyboard (Enter/Space), and escape to clear selection.
- Consistency with existing patterns:
  - Keep existing colors for `status`; selection border sits atop without overriding fill.

5. Technical Plan (Implementation Steps)
- Phase A: Styling
  1) Add Cytoscape stylesheet rule for `node:selected`:
     - border-width: 4–6px; border-color: `#0ea5e9` (sky-500) or `#3b82f6` (blue-500) for consistency with edge:selected.
     - overlay-opacity: 0.08; overlay-color: `#0ea5e9` to provide subtle halo.
     - text-outline-width: 2; text-outline-color to improve label readability.
  2) Add focus class `.focus-dim` applied to graph root (or to all non-selected elements):
     - `node:not(:selected)`: reduce opacity to ~0.55 when focus mode is active.
     - `edge:not(:selected)`: reduce opacity similarly.
  3) Ensure `?is_hidden` style remains respected but selection overrides opacity to at least ~0.8 while selected.

- Phase B: Behavior
  4) In node tap handler:
     - Let Cytoscape manage selection state (`evt.target.select()`), clear previous (`cy.elements().unselect()`), or rely on default `selectionType: 'single'` if enabled.
     - After setting `selectedNodeId`, call a helper `ensureNodeVisibility(n)` that:
       - Expands group if needed; ensures LOD doesn’t hide it; apply temporary bypass.
       - Pans/zooms to keep node in viewport with margin.
  5) Add keyboard handlers:
     - Enter/Space to (de)select hovered node if hover data available; Escape to clear.
  6) When clicking background, clear selection and exit focus-dim mode.

- Phase C: Integration and Performance
  7) Ensure selection-related styles don’t conflict with LOD filters (`applyLOD`). Selected node should always display `display: element`.
  8) Avoid per-frame changes; minimize reflows by toggling one top-level class (e.g., `focus-mode`) on the Cytoscape container.
  9) Persist last selected node id in `sessionStorage` (optional); on load, re-select if node exists.

6. Edge Cases & Risks
- Node hidden (`is_hidden=true`): selecting should temporarily raise opacity and show dashed border remains visible.
- Group nodes (`?is_group`): selection border should be visible over transparent background; consider dotted outline.
- Zoom extremes: at very low zoom outlines can obscure; scale border via `mapData(descendants)` or clamp thickness.
- LOD hiding: selection must force visibility; update LOD function to skip hiding selected element.
- Performance: applying dim to thousands of elements; prefer stylesheet selectors and a boolean CSS class driving a selector context.

7. Milestones and Checklist (Do not delete items; update status inline)
- [ ] Add `node:selected` style in Cytoscape stylesheet.
- [ ] Add focus-dim mode styles for non-selected elements.
- [ ] Update node tap handler to manage selection + ensure visibility.
- [ ] Update background tap to clear selection and focus-dim.
- [ ] Update LOD logic to keep selected visible.
- [ ] Add keyboard accessibility for selection.
- [ ] Persist and restore last selection (optional).
- [ ] QA: contrast and accessibility checks.

8. Manual Testing Steps
- Open a project board.
- Click a node: expect a clear highlight ring and subtle glow; sidebar updates.
- Click background: selection clears; highlight removed; focus-dim off.
- Select an edge: edge highlight remains; node selection cleared.
- Zoom out until LOD hides many nodes: selected node remains visible; is brought into view.
- Toggle node status/priority: selection ring persists; edge target flags update.
- Mark node hidden: selection keeps it visible with dashed border; higher opacity while selected.
- Keyboard: press Escape to clear selection; if supported, Enter on focused node selects it.

9. Rollback Plan
- All changes are confined to `app/templates/project.html` stylesheet and handlers; feature can be disabled by removing new style rules and handler logic.

10. Open Questions
- Should non-selected dim be a user toggle in UI?
- Border and glow color theme: match edge:selected (`#0ea5e9`) or brand blue (`#3b82f6`)?

11. Next Action
- Await confirmation to proceed with implementation per this roadmap.


