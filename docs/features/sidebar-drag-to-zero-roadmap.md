## Sidebar Drag-To-Zero Width – Roadmap

### Status
- Owner: core UI
- Created: 2025-09-07
- State: Implemented (pending QA)

### Initial Prompt (English)
There is a handle in the sidebar that allows dragging to adjust its width. It is possible to drag so that the sidebar takes 100% width, but it is not possible to drag so that it takes 0% width. Fix this.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document all discovered and tried issues, nuances and solutions in as much detail as possible, if any. As you progress with the task, you will use this file as a to-do checklist, keep updating this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items; you may only update their status and add comments. If during implementation it becomes clear that something needs to be added to the tasks – add it to this document. This will help us preserve the context window, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this exact prompt translated to English into the plan (you can name it something like "Initial Prompt"). This is needed to preserve the context of the task in our roadmap file as accurately as possible without the "broken telephone" effect.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.


### Context and Current Behavior
- The main project UI lives in `app/templates/project.html`.
- Sidebar width is controlled by a resizer: `#resizer` (1px wide) between the graph container and `aside#sidebar`.
- Current implementation allows resizing up to the full available width (effectively 100%).
- Minimum width is clamped at 260 px, which prevents dragging the sidebar down to 0 px.

Key code locations:

```2375:2445:app/templates/project.html
        // Sidebar resizer
        (function setupResizer(){
          const resizer = document.getElementById('resizer');
          const sidebar = document.getElementById('sidebar');
          const MIN_SIDEBAR = 260;
          const MIN_LEFT = 0; // allow full-width sidebar
          function getContainer(){ return resizer && resizer.parentElement ? resizer.parentElement : (sidebar && sidebar.parentElement ? sidebar.parentElement : document.body); }
          function computeMaxSidebar(){
            const container = getContainer();
            const containerWidth = container ? container.clientWidth : window.innerWidth;
            const resizerWidth = resizer ? (resizer.offsetWidth || 0) : 0;
            const maxSidebar = containerWidth - resizerWidth - MIN_LEFT;
            return Math.max(MIN_SIDEBAR, maxSidebar);
          }
          function applyWidthClamped(px){
            const clamped = Math.max(MIN_SIDEBAR, Math.min(computeMaxSidebar(), px));
            sidebar.style.width = clamped + 'px';
            return clamped;
          }
          function loadWidth(){
            const w = parseInt(localStorage.getItem('sidebarWidth') || '384', 10);
            applyWidthClamped(w);
          }
          loadWidth();
          let dragging = false;
          let startX = 0;
          let startW = 384;
          resizer.addEventListener('mousedown', (e) => {
            dragging = true; startX = e.clientX; startW = sidebar.offsetWidth;
            document.body.classList.add('select-none'); document.body.style.cursor = 'col-resize';
            e.preventDefault();
          });
          window.addEventListener('mouseup', () => {
            if (!dragging) return;
            dragging = false;
            document.body.classList.remove('select-none');
            document.body.style.cursor = '';
            localStorage.setItem('sidebarWidth', parseInt(sidebar.style.width||'384',10));
          });
          window.addEventListener('mousemove', (e) => {
            
            // Dragging left should INCREASE width, right should decrease
            const delta = startX - e.clientX; // left: positive, right: negative
            const proposed = startW + delta;
            applyWidthClamped(proposed);
            cy.resize();
          });
          // Re-clamp on window resize to avoid overflow when viewport shrinks
          window.addEventListener('resize', () => {
            applyWidthClamped(parseInt(sidebar.style.width||'384',10));
            try { cy.resize(); } catch {}
          });
          // Hide resizer if sidebar hidden
          function syncResizer(){ resizer.style.display = (localStorage.getItem('sidebarHidden') === '1') ? 'none' : ''; }
          syncResizer();
          toggleBtn.addEventListener('click', () => { setTimeout(() => { syncResizer(); cy.resize(); }, 0); });
        })();
```

Observation:
- `MIN_SIDEBAR = 260` is the only thing preventing 0 px. Everything else already supports dynamic max and persistence.
- When width is 0, the resizer remains accessible because it sits to the left of the sidebar in the DOM.


### Goals
- Allow dragging the sidebar down to 0 px (0% of available width) while keeping the current ability to expand up to 100%.
- Keep UX smooth and predictable; graph reflows via `cy.resize()`.
- Persist 0 width across reloads; clamp appropriately on smaller screens.

### Non-Goals
- Changing the overall layout or resizer placement.
- Implementing a new auto-hide behavior (outside of the existing toggle button).

### Design Decisions
- Replace the fixed minimum width with a param that can be 0. Use a small visual threshold (e.g., apply a `collapsed` style below 8 px) to avoid stray padding/border slivers.
- Preserve dynamic max sidebar width as currently implemented.
- Keep existing `localStorage` key (`sidebarWidth`); allow storing and restoring `0`.

### Implementation Plan (High-Level)
1) Clamp Update
   - Change `MIN_SIDEBAR` from `260` to `0`.
   - Keep `MIN_LEFT = 0` to allow 100% sidebar width.

2) Apply Collapsed Style (near-zero UX polish)
   - When `sidebar.offsetWidth < 8`, add a `collapsed` class to `#sidebar` that removes inner padding and hides overflow.
   - Remove the class when width >= 8.

3) Persistence and Load
   - Ensure `loadWidth()` and mouseup handler properly persist `0`.
   - On window resize, re-clamp current width (including `0`) and call `cy.resize()`.

4) Accessibility and Feedback
   - Maintain visible resizer at all times when the sidebar is visible.
   - Optional: add `aria-label` to the resizer.

5) Regression Guard (Comments Fullscreen logic)
   - Comments fullscreen currently enforces a minimum of 260 px for the sidebar. Keep that logic unchanged (separate feature), but ensure it cleanly restores previous width including `0`.

### Acceptance Criteria
- Sidebar can be dragged to 0 px width; resizer remains operable.
- Sidebar can be dragged back to a usable width from 0 px.
- Width persists across reloads; `0` is restored correctly and re-clamped on viewport resize.
- No layout shifts, no console errors; graph area resizes via `cy.resize()`.
 - Toggle button behavior: when width < 5% and visible → collapse to 0 on click; when width = 0 or hidden → expand to default width on click; resizer visibility stays in sync with sidebar visibility.

### Manual Test Plan
1. Open any project page.
2. Drag the resizer rightwards until the sidebar narrows to 0 px.
   - Expect: sidebar shrinks to 0; resizer is still visible and draggable; no layout jitter.
3. Drag the resizer leftwards to restore a usable width.
   - Expect: sidebar expands smoothly; content visible again; padding restored when not collapsed.
4. Refresh the page with the sidebar at 0 px.
   - Expect: width `0` restored; resizer still accessible.
5. Resize the browser window.
   - Expect: graph reflows; no overflow; 0 px remains 0 px.
6. Click Toggle Sidebar to hide, then click again to show.
   - Expect: resizer visibility syncs with sidebar; no loss of handle.
7. Set width to < 5% (but > 0), then click Toggle Sidebar.
   - Expect: width collapses to 0 (visible sidebar, not hidden).
8. With width = 0, click Toggle Sidebar.
   - Expect: width snaps to default (384 px by default), graph resizes, `collapsed` removed.
9. With sidebar hidden via Toggle, click Toggle again.
   - Expect: sidebar shows; if stored width < 5% it snaps to default.
7. Use comments fullscreen toggle and then exit.
   - Expect: width restores to the previous value (including `0` if that was the prior state).

### Risks and Mitigations
- Risk: A 0 px sidebar may confuse users (it looks "gone").
  - Mitigation: resizer remains visible; quick restore by dragging. Optional future hint or double-click snap.

### Rollback Plan
- Revert `MIN_SIDEBAR` to `260` and remove the `collapsed` style hook if any regressions are found.

### Tasks Checklist
- [x] Update clamp to allow min width 0.
- [x] Add `collapsed` styling under 8 px (CSS + toggle logic).
- [x] Verify persistence of `0` width on load and after drag end.
- [x] Re-clamp on window resize; verify `cy.resize()` calls.
- [ ] QA: run the Manual Test Plan; document observations below.

### Additional Enhancements Implemented
- Drag resizing via the Toggle Sidebar button (with click-vs-drag slop and click-cancel after drag).
- Toggle threshold logic (5%):
  - If visible and width < 5%: collapse to 0 px instead of hiding.
  - If width = 0 or hidden: expand to default width on click.
- Resizer visibility synchronization with sidebar visibility to avoid missing the handle after toggling.

### Engineering Notes / Observations Log
- 2025-09-07: Drafted plan; identified single clamp point (`MIN_SIDEBAR`) and optional UX polish via `collapsed` style.
- 2025-09-07: Implemented min 0 clamp, collapsed class toggle (<8 px), persisted 0 width, window re-clamp, and resizer sync.
- 2025-09-07: Added Toggle button drag handle, click threshold logic (<5%) and default snap when width is 0 or hidden.

### Related
- `docs/features/sidebar-resize-full-width-roadmap.md` – prior work enabling dynamic max width and full-width behavior.


