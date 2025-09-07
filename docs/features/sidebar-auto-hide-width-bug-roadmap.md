# Sidebar Auto-Hide/Restore Width Bug – Roadmap

Status: In Progress

## Initial Prompt (translated to English)

When I click on a node, the sidebar expands to the full screen width for some reason. I had manually set the sidebar not to full width but around 25–30%. Then the sidebar auto-hides, and after clicking on the node, it expands to 100% again. Then I reduce it to 25%, it hides, and after clicking again it expands to 100%.

Please analyze the task and project deeply and decide how best to implement the fix.

Create a detailed, step-by-step action plan in a separate document file. We have a `docs/features` folder for this. If there is no such folder, create it. Document all issues, nuances, and solutions discovered and attempted so far. As you progress with the implementation, use this file as a todo/checklist—update it and document what is done, how it is done, what issues arose, and what decisions were made. For history, do not delete items; only update their status and comment. If it becomes clear during implementation that tasks need to be added—add them to this document. This will help keep the context window, remember what has already been done, and not forget what was planned. Remember that only the English language is allowed in code and comments in the project. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Also include manual testing steps, i.e., what needs to be clicked in the interface.

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## Context and Observations

- The sidebar UI and behavior are implemented inside `app/templates/project.html`.
- Relevant logic involves persistence via `localStorage` and handlers for:
  - Auto-hide scheduling/restoration
  - Node tap reveal
  - Toggle button click
  - Resizer drag
  - Task comments fullscreen (which can temporarily maximize the sidebar width)

Code reference (file `app/templates/project.html`, excerpts):

- Reveal on node tap when hidden uses a threshold and defaults to 384px if below threshold:
  ```2109:2639:app/templates/project.html
  // Ensure sidebar reveals on node tap if hidden
  (function wireRevealSidebarOnNodeTap(){
    ...
    cy.on('tap','node', () => {
      ...
      if (localStorage.getItem('sidebarHidden') === '1'){
        ...
        const thresholdPx = Math.max(1, Math.floor(containerWidth * 0.05));
        const DEFAULT_W = 384;
        const curW = parseInt(sidebar.style.width || sidebar.offsetWidth || '0', 10) || 0;
        localStorage.setItem('sidebarHidden','0');
        if (curW < thresholdPx){
          sidebar.style.width = DEFAULT_W + 'px';
          ...
          localStorage.setItem('sidebarWidth', String(DEFAULT_W));
        }
        applySidebarVisibility();
      }
    });
  })();
  ```

- Toggle button click logic has similar defaulting when width is very small, otherwise hides:
  ```2499:2560:app/templates/project.html
  // Toggle sidebar
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('btnToggleSidebar');
  function applySidebarVisibility(){ ... }
  toggleBtn.addEventListener('click', () => {
    const hidden = localStorage.getItem('sidebarHidden') === '1';
    const DEFAULT_W = 384;
    ...
    const thresholdPx = Math.max(1, Math.floor(containerWidth * 0.05));
    const curW = parseInt(sidebar.style.width || sidebar.offsetWidth || '0', 10) || 0;
    if (hidden){
      localStorage.setItem('sidebarHidden', '0');
      if (curW < thresholdPx){
        sidebar.style.width = DEFAULT_W + 'px';
        localStorage.setItem('sidebarWidth', String(DEFAULT_W));
      }
      applySidebarVisibility();
      return;
    }
    ...
    localStorage.setItem('sidebarHidden', '1');
    applySidebarVisibility();
  });
  applySidebarVisibility();
  ```

- Auto-hide stores previous width in `sidebar.prevWidthAutoHidden` and restores using it; if absent, falls back to `sidebarWidth` or 384:
  ```2577:2610:app/templates/project.html
  function scheduleAutoHide(){
    ...
    autoHideTimer = setTimeout(()=>{
      const curW = parseInt(sidebar.style.width || sidebar.offsetWidth || '0', 10) || 0;
      if (getRespectZero() && curW === 0) return;
      localStorage.setItem('sidebar.prevWidthAutoHidden', String(curW));
      localStorage.setItem('sidebarHidden','1');
      applySidebarVisibility();
    }, getAutoHideDelay());
  }
  function restoreFromAutoHide(){
    localStorage.setItem('sidebarHidden','0');
    const prev = parseInt(localStorage.getItem('sidebar.prevWidthAutoHidden')||localStorage.getItem('sidebarWidth')||'384',10);
    const w = applyWidthClamped(prev);
    localStorage.setItem('sidebarWidth', String(w));
    applySidebarVisibility();
  }
  ```

- Comments fullscreen can set the sidebar to the maximum possible width and writes that to `sidebarWidth`:
  ```2939:2984:app/templates/project.html
  const FS_KEY = 'sidebar.task.comments.fullscreen';
  function applyFullscreen(state){
    ...
    if (state){
      const maxSidebar = Math.max(260, containerWidth - resizerWidth);
      const prevW = parseInt(sidebar.style.width || sidebar.offsetWidth || '384', 10);
      localStorage.setItem('sidebar.prevWidthB4CommentsFs', String(prevW));
      sidebar.style.width = maxSidebar + 'px';
      localStorage.setItem('sidebarWidth', String(maxSidebar));
      ...
    } else {
      const prev = parseInt(localStorage.getItem('sidebar.prevWidthB4CommentsFs') || '384', 10);
      sidebar.style.width = prev + 'px';
      localStorage.setItem('sidebarWidth', String(prev));
      ...
    }
  }
  ```

## Hypothesis – Why it sometimes expands to 100%

- In some flows, `restoreFromAutoHide()` may fall back to `sidebarWidth` instead of the specifically saved `sidebar.prevWidthAutoHidden` (e.g., if the previous value is missing/cleared). If `sidebarWidth` had been set to a maximum value earlier (e.g., by comments fullscreen), restoration will clamp to container max, effectively appearing as 100%.
- Another contributing factor: width threshold logic for reveal uses a fixed `DEFAULT_W` but does not explicitly restore the last manual width unless present.

## Goals / Acceptance Criteria

- When the sidebar auto-hides and is then revealed (by node tap, edge hover, or toggle), it restores to the last meaningful user-set width, not to the maximum width.
- Comments fullscreen should not permanently overwrite the “normal” sidebar width. Fullscreen width must be treated as temporary.
- Existing behaviors (collapse to 0px, threshold default, auto-hide timing, edge reveal) continue to work and remain intuitive.

## Implementation Plan

1) Storage model adjustments (SoC, predictability)

- Introduce clearer keys and do not overload them:
  - `sidebar.width.current`: last committed normal width (updated on resizer mouseup and on non-fullscreen restore paths).
  - `sidebar.width.prevBeforeAutoHide`: value saved right before auto-hide.
  - `sidebar.width.prevBeforeFs`: value saved right before entering fullscreen.
- Stop writing fullscreen width into `sidebarWidth` (or repoint all current reads/writes to `sidebar.width.current`). Fullscreen changes should only affect DOM width and `sidebar.width.prevBeforeFs`.

2) Restore logic

- In `restoreFromAutoHide()` use strictly `sidebar.width.prevBeforeAutoHide` if available; only fallback to `sidebar.width.current` and lastly to default (384). Avoid using any fullscreen-specific values.
- On reveal by node tap or toggle, if a width exists in `sidebar.width.current`, apply it instead of defaulting immediately to 384 when `curW < thresholdPx`.

3) Resizer persistence

- On mouseup after resizing, store the clamped width to `sidebar.width.current`.
- Maintain the `collapsed` class toggling for near-zero widths.

4) Fullscreen behavior isolation

- On entering comments fullscreen:
  - Save `sidebar.width.prevBeforeFs` (from current DOM width).
  - Apply max width to the DOM only. Do not touch `sidebar.width.current`.
- On exiting fullscreen:
  - Restore the DOM width from `sidebar.width.prevBeforeFs`.
  - Update `sidebar.width.current` with the restored width.

5) One-time migration and backward compatibility

- If legacy keys exist (`sidebarWidth`, `sidebar.prevWidthAutoHidden`, `sidebar.prevWidthB4CommentsFs`), migrate them once at load time to the new keys, then continue only with the new keys.

6) Optional UX guardrails

- Consider capping restored width to a percentage of container (e.g., max 80–90%) unless explicitly in fullscreen.
- Ensure `applyWidthClamped` consistently clamps to container bounds and maintains `collapsed` class behavior.

## Manual Test Plan

Perform these on desktop with varying window sizes:

1) Basic auto-hide/restore
- Set sidebar to ~25–30% width via resizer.
- Trigger auto-hide (click outside or pan to schedule, wait for delay).
- Reveal by clicking on a node.
- Expected: width restores to ~25–30%, not full width.

2) Toggle button reveal
- With sidebar hidden, click the toggle button.
- Expected: restores to the last meaningful width, not to full width and not always to 384 unless nothing was stored.

3) Edge hover reveal
- Hide the sidebar. Move pointer to the right edge to trigger reveal.
- Expected: restores to last width.

4) Fullscreen comments interaction
- Set sidebar to ~30%.
- Enter comments fullscreen.
- Exit fullscreen.
- Trigger auto-hide and then restore.
- Expected: normal restore uses pre-fullscreen width (~30%); fullscreen does not persist as the normal width.

5) Zero-width case
- Drag to 0px and release. Hide and reveal.
- Expected: if "respect zero" is enabled, do not auto-hide or restore away from 0 without explicit user action.

6) Browser refresh / BFCache
- Refresh page. Repeat the above flows.
- Expected: the corrected storage model survives refresh, with no accidental expansion to full width.

## Tasks & Checklist

- [ ] Introduce new storage keys (`sidebar.width.current`, `sidebar.width.prevBeforeAutoHide`, `sidebar.width.prevBeforeFs`).
- [ ] Migrate legacy keys on load and centralize accessors (get/set helpers).
- [ ] Update resizer mouseup to write `sidebar.width.current`.
- [ ] Update node tap and toggle reveal to prefer `sidebar.width.current` when present.
- [ ] Update `restoreFromAutoHide()` to rely on `sidebar.width.prevBeforeAutoHide`.
- [ ] Isolate fullscreen behavior so it does not write to normal width key.
- [ ] Add optional guardrail: cap non-fullscreen restored width to max percentage.
- [ ] QA: Manual test plan scenarios 1–6 on varying window sizes.
- [ ] Documentation updates in this roadmap with outcomes and any adjustments.

## Risks & Rollback

- Risk: Key migration could cause unexpected first-load states if old keys contain extreme values. Mitigation: safe defaults and clamps.
- Risk: Edge cases with very narrow containers can make 384px impossible. Mitigation: always clamp to container.
- Rollback: Keep changes localized to template JS; feature-flag behind a `localStorage` toggle during testing if needed.

## Open Questions

- Should there be a hard max percentage for non-fullscreen states (e.g., 90%)?
- Should default width remain 384px or be percentage-based for responsiveness?


