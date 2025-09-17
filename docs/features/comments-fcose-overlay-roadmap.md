### Feature: Remove stray "fcose" text overlay in Comments panel

#### Initial Prompt (translated)

Look at the screenshot. Why do I see "fcose" in the middle of the comments page? I highlighted it in a red frame.

=== Analyse the Task and project ===

Deeply analyze our task and project and decide how best to implement it.

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate file-document. We have a `docs/features` folder for this. If there is no such folder, create it. Document in this file all discovered and tried problems, nuances, and solutions as much as possible. As you progress with the implementation of this task, you will use this file as a todo checklist, updating it and documenting what is done, how it is done, what problems occurred, and what decisions were made. For history, do not delete items; you can only update their status and comment. If during the implementation it becomes clear that something needs to be added, add it to this document. This will help us preserve context, remember what we have already done, and not forget what was planned. Remember that only the English language is allowed in code and comments, project labels. When you have written the plan, stop and ask me if I agree to start implementing it or if anything needs adjustment in it.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the UI.

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

=== Get time from MCP Server ===

If you need the current time. Get it from the time MCP Server.

---

## 1) Context and Current Behavior

- The graph page is rendered by `app/templates/project.html`.
- A toolbar above the Cytoscape canvas includes a layout section with two selects: `#layoutMode` and `#layoutAlgo`.
- `#layoutAlgo` contains options including `fcose`, `dagre`, etc. It is placed inside the top toolbar (outside the sidebar).
- The Comments panel can be toggled to fullscreen via the `Fullscreen` button (`#btnCommentsFullscreen`). Fullscreen hides other sidebar blocks and maximizes the comments region height and the sidebar width but does not hide or z-index-isolate the top toolbar of the main content area.
- Native HTML `select` controls render their dropdowns and visible value text above many stacking contexts on Windows; moreover, our toolbar remains visible behind the sidebar. As a result, the `#layoutAlgo` control leaks visually into the Comments area when the layout places it under the editor viewport, making its current value text (`fcose`) appear in the middle of the comments section.

Evidence in code:

```80:137:app/templates/project.html
<select id="layoutAlgo" class="border rounded px-2 py-1 text-sm" title="Algorithm">
  <option value="fcose">fcose</option>
  <option value="dagre">dagre</option>
  <option value="cose-bilkent">cose-bilkent</option>
  <option value="cose">cose</option>
  <option value="concentric">concentric</option>
  <option value="grid">grid</option>
</select>
```

The Comments fullscreen logic changes height and width but does not manage global z-index or visibility of the main toolbar area.

## 2) Root Cause

- UI layering: The main graph toolbar is still present and can overlap the sidebar area on certain viewport sizes. The `select#layoutAlgo` (with visible text "fcose") sits underneath the Comments editor area; with native rendering/z-index, its box/text can show through.
- No `z-index` isolation: `#sidebar` (comments) does not create a higher stacking context than the main content, or the toolbar is not masked/hidden.
- No conditional hiding: When Comments go fullscreen, we do not hide or `pointer-events: none` the main toolbar region.

## 3) Goals

- Prevent any main toolbar controls (especially native selects) from appearing over or through the Comments area.
- Keep interactions intuitive and accessible.
- Avoid regressions to graph interactions and layout controls when not in comments fullscreen mode.

## 4) Options Considered

1. Hide or visually move the layout controls when Comments fullscreen is active.
   - Pros: Simple, robust, minimal CSS.
   - Cons: Controls unavailable while reading comments fullscreen (acceptable).

2. Raise `#sidebar` over main content via `position: relative` and high `z-index`, and ensure main content has a lower stacking context.
   - Pros: Keeps controls; no DOM changes.
   - Cons: Native select dropdowns may still render above; needs testing on Windows.

3. Replace native `select` with a custom dropdown component.
   - Pros: Full control over stacking.
   - Cons: Overkill for this bug; more code.

Decision: Implement 1 + 2 together for reliability on Windows.

## 5) Implementation Plan

Step A — CSS layering
- Ensure `#sidebar` has a higher stacking context than the graph toolbar: give `#sidebar` `position: relative; z-index: 50` (or higher than the graph header). The graph toolbar wrapper can get a base `z-index: 10` if needed.

Step B — Fullscreen state handling
- In `applyFullscreen(state)` (already toggling comments fullscreen), also add a CSS class on the root container to indicate comments fullscreen, e.g., `document.body.classList.toggle('comments-fs', state)`.
- In this state:
  - Hide or disable the layout section in the toolbar with a class (e.g., `.graph-layout-toolbar { display: none; }`) or set `visibility: hidden`.
  - Alternatively, add `pointer-events: none; opacity: 0;` to the toolbar to prevent visual bleed while keeping layout.

Step C — DOM hooks
- Wrap layout controls with a container `<div class="graph-layout-toolbar"> ... </div>` if not already grouped, to make toggling easy.

Step D — Accessibility
- When hidden via CSS during fullscreen, ensure controls are not focusable: use `aria-hidden="true"` toggle or `inert` attribute if supported.

## 6) Manual Test Plan

Baseline
1. Open a project graph page.
2. Verify the toolbar shows `Layout` and `Algorithm` (`fcose` selected by default).
3. Select a node; verify comments area renders normally (no overlay text).

Reproduce (pre-fix)
4. Resize the window so the comments area vertically aligns with the toolbar region.
5. Observe stray `fcose` text appearing around the comments editor.

Verify Fix
6. Click `Comments → Fullscreen`.
7. Confirm the toolbar is hidden or non-interactive, and no text from it appears in the comments area.
8. Scroll and type in the editor; ensure no overlay appears.
9. Exit fullscreen; verify the toolbar returns and is usable.

Regression Checks
10. Run layout algorithms (`fcose`, `dagre`) after exiting fullscreen.
11. Confirm graph interactions (pan/zoom/select) remain unaffected.
12. Confirm keyboard focus does not tab into hidden toolbar while fullscreen (try Tab).

## 7) Risks & Mitigations

- Native select rendering may still pop over if not hidden: mitigate by hiding the container in fullscreen.
- Z-index wars with other overlays (modals, tooltips): centralize stacking indices and document them.

## 8) Acceptance Criteria

- No stray text (e.g., `fcose`) appears in the Comments panel in any layout or fullscreen state.
- Comments fullscreen shows only comment-related UI within the sidebar area.
- Toolbar reappears and works normally after exit.

## 9) Work Log / Checklist

- [ ] Add high z-index to `#sidebar` and base z-index to graph toolbar.
- [ ] Add `comments-fs` state to `body` in `applyFullscreen()`; toggle class.
- [ ] Wrap layout controls with `.graph-layout-toolbar` or add an id for easier toggling.
- [ ] CSS: `.comments-fs .graph-layout-toolbar { display: none; }`.
- [ ] A11y: prevent focus on hidden toolbar (`aria-hidden` or `inert`).
- [ ] Manual testing across Chrome/Edge on Windows.

Notes:
- Keep all UI text and code comments in English.
- Follow SOLID, DRY, KISS, and clean code practices; minimal surface change.


