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
- The layout controls (previously in the top header toolbar) have been moved to Sidebar → Settings → Graph Layout. They are no longer present in the header.
- The Comments panel can be toggled to fullscreen via the `Fullscreen` button (`#btnCommentsFullscreen`).
- Previously, native HTML `select` controls in the header could bleed over the comments area on Windows due to stacking contexts, causing visible text like `fcose` to appear. This scenario is now obsolete after relocation.

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

## 2) Root Cause (historical)

- UI layering and native select rendering in the header toolbar caused leaks into the Comments area. This is no longer applicable after moving layout controls into the sidebar.

## 3) Goals

- Prevent any main toolbar controls (especially native selects) from appearing over or through the Comments area.
- Keep interactions intuitive and accessible.
- Avoid regressions to graph interactions and layout controls when not in comments fullscreen mode.

## 4) Options Considered (historical)

1. Hide or visually move the layout controls when Comments fullscreen is active.
   - Pros: Simple, robust, minimal CSS.
   - Cons: Controls unavailable while reading comments fullscreen (acceptable).

2. Raise `#sidebar` over main content via `position: relative` and high `z-index`, and ensure main content has a lower stacking context.
   - Pros: Keeps controls; no DOM changes.
   - Cons: Native select dropdowns may still render above; needs testing on Windows.

3. Replace native `select` with a custom dropdown component.
   - Pros: Full control over stacking.
   - Cons: Overkill for this bug; more code.

Decision (historical): Initially considered CSS/z-index adjustments and conditional hiding. Final resolution achieved by relocating controls to the sidebar.

## 5) Implementation Plan (current)

- No additional CSS layering or hiding is required, as header layout controls no longer exist. Ensure Sidebar has appropriate `z-index` (already set) and continues to function in fullscreen.

## 6) Manual Test Plan

Baseline
1. Open a project graph page.
2. Verify there is no layout toolbar in the header; layout controls are under Settings → Graph Layout.
3. Select a node; verify comments area renders normally (no overlay text).

Reproduce (pre-fix)
4. Resize the window so the comments area vertically aligns with the toolbar region.
5. Observe stray `fcose` text appearing around the comments editor.

Verify (after relocation)
6. Click `Comments → Fullscreen`.
7. Confirm no header toolbar exists and no stray layout text appears in the comments area.
8. Scroll and type in the editor; ensure no overlay appears.
9. Exit fullscreen; verify Sidebar remains functional and Graph Layout controls are accessible under Settings.

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

- [x] Relocate layout controls from header to Sidebar → Settings → Graph Layout (resolves bleed issue at the root).
- [x] Keep `#sidebar` with a higher z-index than main content.
- [x] Manual testing across Chrome/Edge on Windows after relocation.

Notes:
- Keep all UI text and code comments in English.
- Follow SOLID, DRY, KISS, and clean code practices; minimal surface change.


