### Feature: Sidebar can resize up to 100% width (Roadmap)

This document tracks the plan, decisions, and progress to allow the right sidebar to resize in a much wider range, including expanding to the full screen width when desired.

### Initial Prompt (translated)

We have a sidebar whose width can be changed by dragging with the mouse. I would like the sidebar width to be adjustable within wider bounds, for example, to expand it to 100% of the screen width.

=== Analyse the Task and project ===

Deeply analyze our task and project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of action to implement this task in a separate document file. We have a folder `docs/features` for this. If there is no such folder, create it. Capture in the document as comprehensively as possible all discovered and tried problems, nuances, and solutions, if any. As you progress with this task, you will use this file as a todo checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and comment. If in the course of implementation it becomes clear that something needs to be added to the tasks, add it to this document. This will help us keep the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include in the plan steps for manual testing: what needs to be clicked in the interface.

==================================================

### Context and Current Implementation

- The sidebar and resizer live in `app/templates/project.html` within the main layout.
- Current clamp logic in JS (persisted in `localStorage` under `sidebarWidth`) limits width to 260..560 px:

```startLine:endLine:app/templates/project.html
1738:          function loadWidth(){
1739:            const w = parseInt(localStorage.getItem('sidebarWidth') || '384', 10);
1740:            const clamped = Math.max(260, Math.min(560, w));
1741:            sidebar.style.width = clamped + 'px';
1742:          }
```

```startLine:endLine:app/templates/project.html
1761:            // Dragging left should INCREASE width, right should decrease
1762:            const delta = startX - e.clientX; // left: positive, right: negative
1763:            const newW = Math.max(260, Math.min(560, startW + delta));
1764:            sidebar.style.width = newW + 'px';
1765:            cy.resize();
```

- Layout: left content is a flex column (`flex-1 min-w-0`), then `#resizer` (fixed width), then `aside#sidebar` (inline `style="width: 384px;"`). The left area can shrink because of `min-w-0`, enabling the sidebar to grow large if we relax the clamp.
- `cy.resize()` and LOD re-application already run on resize/toggle.

### Goals

- Allow the sidebar to resize up to the full available width (100% of the container/screen), not limited by 560 px.
- Preserve minimum sidebar usability width (keep a sane minimum, e.g., 240–260 px).
- Maintain smooth UX and performance; the graph should reflow correctly via `cy.resize()`.
- Persist width across sessions; clamp dynamically on load according to the current viewport.

### Non-Goals

- Changing the overall page structure or switching the resizer position is out of scope.
- Introducing a second resizable panel is out of scope.

### UX Requirements

- Dragging the resizer to the left expands the sidebar; dragging to the right shrinks it (current behavior preserved).
- The resizer always remains visible when the sidebar is visible.
- Optional niceties (future): double-click the resizer to snap to default width; keyboard accessibility for resizing.

### Technical Approach

1. Replace hard-coded max clamp `560` with a dynamic calculation based on the container width.
   - Compute `const container = resizer.parentElement;` (or the main flex container) and measure `container.clientWidth`.
   - Calculate `maxSidebar = container.clientWidth - resizer.offsetWidth - minLeftWidth`.
     - `minLeftWidth` can be set to `0` to allow the sidebar to occupy 100% width, or a small guard (e.g., `0`–`24`) if we want a sliver of graph.
   - Ensure `maxSidebar` is at least `minSidebar`.

2. Update both load and drag paths to use the dynamic clamp:
   - On load width: clamp the stored width to `[minSidebar, maxSidebarAtLoad]`.
   - During mousemove while dragging: clamp based on the current container width (so it adapts when the window changes during drag).

3. Persist width to `localStorage` after drag end (keep existing behavior).

4. Handle window resize:
   - On `resize`, re-clamp the current `sidebar.style.width` to the new `maxSidebar` and call `cy.resize()`.
   - This prevents overflow when restoring a wide width on smaller screens.

5. Keep existing hooks: ensure LOD and filters re-apply after resize; this is already done via existing calls.

6. Optional enhancements (to be decided):
   - Double-click resizer to toggle between default width and last expanded width.
   - Add an accessibility label and larger hit area for the resizer.

### Edge Cases and Considerations

- Full-width sidebar (graph area shrinks to 0): the left pane has `min-w-0`, so this is acceptable; `cy.resize()` should handle 0 width gracefully.
- Margins on the left graph container (`mx-4`) are inside the left pane; with 0 width they won’t show. No layout breaking expected.
- Extremely small screens: dynamic clamping ensures the sidebar width never exceeds the container width.
- Persisted oversize after a previous session: clamped on load.

### Acceptance Criteria

- Sidebar can expand to occupy up to 100% of the available width.
- Minimum width respected (≥ 240–260 px).
- Width persists across reloads; on smaller screens the width is clamped appropriately.
- Graph resizes smoothly and remains interactive after any sidebar resize/toggle.
- No console errors; no visual layout breaks.

### Manual Test Plan

1. Open a project page.
2. Drag the resizer slowly to the left until the sidebar fills the screen.
   - Expected: the graph area shrinks to 0; no layout overflow or jitter.
3. Drag the resizer to the right to the minimum width.
   - Expected: clamped at the minimum; layout remains stable.
4. Refresh the page.
   - Expected: the sidebar restores to the last width; if too large for the current viewport, it is clamped and fits.
5. Click “Toggle Sidebar” to hide, then show again.
   - Expected: the resizer visibility follows the sidebar; width persists after showing; graph updates correctly.
6. Resize the browser window (narrower and wider) with a wide sidebar set.
   - Expected: width re-clamps without overflow; graph updates.
7. Interact with the graph (zoom, pan, select nodes) after resizing.
   - Expected: `cy.resize()` has been applied; interactions work; LOD still behaves per settings.

### Implementation Tasks Checklist

- [ ] Replace hard-coded max clamp with dynamic calculation based on container width.
- [ ] Update `loadWidth()` to clamp with dynamic max and set style.
- [ ] Update mouse `mousemove` handler to clamp with dynamic max and call `cy.resize()`.
- [ ] Add `window.addEventListener('resize', ...)` to re-clamp and `cy.resize()`.
- [ ] QA pass against the Manual Test Plan; document any quirks.
- [ ] Optional: double-click resizer to snap to default width.

### Risks and Rollback

- Risk: Full-width sidebar may surprise users by hiding the graph entirely. Mitigation: easy drag back; optional future snap behavior.
- Risk: Very small screens. Mitigation: dynamic clamp; ensure a sensible minimum.
- Rollback: Revert to prior fixed max clamp (560 px) by restoring the previous constants.

### Notes

- Keep all code comments and labels in English (project convention).
- Maintain SOLID, DRY, KISS, Separation of Concerns; keep resize logic self-contained.

### Timestamps

- 2025-09-04T00:00:00Z — Document created; awaiting approval to implement.


