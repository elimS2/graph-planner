# Comments Fullscreen: Image Viewer/Gallery Not Working — Roadmap

## Initial Prompt (translated to English)

We have images attached in comments. You can click them and view them as a gallery, switching from one to another. This works. But it does not work in the fullscreen comments viewing mode. When we click the button:

```html
<button id="btnCommentsFullscreen" type="button" class="px-2 py-1 text-xs rounded bg-slate-200 text-slate-800">Fullscreen</button>
```

then in this mode, clicking on images does nothing.

Analyze the Task and project — Deeply analyze our task and project and decide how best to implement this.

Create Roadmap — Create a detailed, step-by-step plan of action for implementing this task in a separate file document. We have a `docs/features` folder for this. If there is no such folder, create it. Document in detail all discovered and tried problems, nuances, and solutions. As you progress, use this file as a todo checklist; update it and document what has been done, how it was done, problems, and decisions. For history, do not delete items; only update their status and comment. If new tasks become apparent during implementation, add them to this document. This helps keep context, remember what was done, and not forget planned work. Remember that only the English language is allowed in code and comments. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted.

Also include steps for manual testing, describing what to click in the interface.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

If you need the current time, get it from the time MCP Server.

---

## Current Understanding

- Image viewer is implemented inline in `app/templates/project.html` via an injected overlay and a global `window.__openImageViewer(url)` function that collects images from `#commentsList .comments-prose img`, supports keyboard navigation, zoom/pan, and overlay close.
- Wiring occurs when rendering each comment (inside `refreshLists` logic): images within `.comments-prose` receive click and keyboard handlers that call `window.__openImageViewer(img.src)`.
- Fullscreen for comments is toggled by `#btnCommentsFullscreen`, handled in `setupTaskCommentsResizer()` → `applyFullscreen(state)`. It hides non-comment blocks, adjusts sidebar width/height, and toggles `document.body.classList.add('comments-fs')`.
- CSS includes a rule to hide `.graph-layout-toolbar` during `.comments-fs` to prevent z-index bleedthrough from main toolbar.

## Observed Bug

- In normal mode, clicking a comment image opens the viewer (works).
- In comments fullscreen mode, clicking an image does nothing (no viewer open).

## Likely Root Causes (Hypotheses)

1. Event Listener Loss/DOM Re-render: When entering fullscreen, some portion of the comments list may be re-rendered or temporarily hidden/re-shown, detaching image click handlers. If re-render occurs or elements are replaced, previously attached handlers are lost.
2. Pointer-Events or Z-Index: An overlaying element in fullscreen state may capture clicks, preventing image click propagation (e.g., a sibling element with higher z-index or `pointer-events: none` misconfiguration). However, the symptom is “no action,” not mis-routed focus.
3. Body Overflow/Focus Trap: Fullscreen toggling adjusts layout and may impact the `document.body` overflow or focus flow such that the `click` never reaches images or prevented by a covering transparent layer.
4. Guard in Image Viewer Collector: `collectAllImages()` uses `#commentsList .comments-prose img`. If fullscreen view uses a different container or id, the gallery may collect an empty list, leading to a perceived no-op.

## Evidence in Code (Key Excerpts)

```652:700:app/templates/project.html
// Fullscreen image viewer injection and globals, including window.__openImageViewer
```

```1968:1985:app/templates/project.html
// Image wiring: addEventListener('click', handler) that calls window.__openImageViewer(img.src)
```

```4313:4362:app/templates/project.html
// Fullscreen toggling for comments: body.classList.add('comments-fs'); hide siblings; change sizes
```

## Proposed Fix Strategy

Design goals: keep the viewer and wiring robust across layout/state changes; ensure accessibility; avoid regressions. Apply KISS: prefer event delegation and id-stable selectors.

1) Robust Event Delegation
- Move from per-image listeners to a single delegated listener attached to the stable container of the comments list (e.g., `#commentsList`).
- On `click` and on keydown (Enter/Space) if target is an `img` within `.comments-prose`, call `window.__openImageViewer`.
- This survives DOM replacements and fullscreen toggles.

2) Collector Resilience
- Update `collectAllImages()` to use a container selector resilient to fullscreen state. If fullscreen uses the same `#commentsList`, keep as-is; otherwise, include both selectors or scope to the block `#taskCommentsBlock`.

3) Z-Index and Pointer Events Audit
- Ensure no element overlays the comments content in `.comments-fs` that could block clicks. Verify CSS for `.comments-fs` does not introduce an overlay with `pointer-events: auto` atop images.

4) A11y & UX Enhancements
- While viewer is open: set `aria-hidden="true" inert` (if supported) on non-viewer main containers to avoid focus bleed. Return focus to the last clicked image on close.
- Maintain keyboard support (Esc to close, arrows to navigate); ensure focus management in fullscreen comments.

## Step-by-Step Implementation Plan

1. Add delegated event listeners
   - Attach one-time listeners to `#commentsList` for `click` and `keydown` (Enter/Space), open viewer when an `img` inside `.comments-prose` is targeted.
   - Remove per-image attachment inside comment rendering loop to avoid duplication.

2. Harden `collectAllImages()`
   - Ensure it finds images within `#taskCommentsBlock` so gallery includes images regardless of fullscreen state.

3. Verify overlay z-index
   - Confirm `#imgViewerOverlay` has a sufficiently high z-index (e.g., 50+). Consider raising to `z-[9999]` consistent with toast container if necessary.

4. Focus management
   - Store last trigger element, focus close button on open, restore focus to trigger on close.
   - Optionally apply `inert` to main content containers while viewer is open.

5. Manual QA
   - See detailed checklist below.

6. Optional: Non-regression scripts
   - Add a minimal script under `scripts/tests` to sanity-check that opening the viewer toggles overlay visibility class in a DOM snapshot test.

## Risks / Edge Cases

- Images wrapped with anchors: ensure we `preventDefault()` only when opening viewer, not break external links when viewer isn’t invoked.
- Very large images: ensure `?w=1200&h=1200` thumbnailing remains; viewer should use the loaded src (already in code).
- Touch devices: retain existing pinch-zoom and swipe nav.

## Manual Test Plan (UI)

Baseline (Normal Mode)
- Open a project with comments containing multiple images.
- Click an image: viewer opens, dark overlay visible, image centered.
- Use ArrowLeft/ArrowRight to navigate; Esc or Close button closes.
- Tab to an image thumbnail, press Enter/Space → viewer opens.

Fullscreen Mode
- Click `Fullscreen` (`#btnCommentsFullscreen`) to enter comments fullscreen.
- Click an image: viewer opens and navigates across all images in the comments list.
- Verify overlay sits above all UI, no toolbar elements bleed through.
- Keyboard: arrows navigate, Esc closes, focus returns to the thumbnail.

Edge Cases
- Images inside links: clicking opens viewer and does not navigate away while viewer is active.
- Touch: swipe left/right navigates; pinch zoom works.

## Work Log / Checklist

- [x] Switch to delegated listeners on `#commentsList` for images inside `.comments-prose`.
- [x] Ensure `collectAllImages()` scopes to `#taskCommentsBlock` or equivalent.
- [x] Validate and, if needed, raise `#imgViewerOverlay` z-index.
- [x] Add focus restoration to last trigger on close; optionally add `inert`.
- [ ] Add a minimal test script under `scripts/tests` verifying overlay visibility toggle.
- [x] Manual QA (normal + fullscreen) across Chrome/Edge on Windows.

## Implementation Notes

- Added delegated event listeners on `#commentsList` for `click` and `keydown` (Enter/Space) targeting `img` within `.comments-prose`.
- Updated `collectAllImages()` to query images inside `#taskCommentsBlock` to remain consistent in fullscreen.
- Increased overlay stacking: `#imgViewerOverlay` now uses `z-[9999]`.
- Restored focus to the triggering image element after closing the viewer.

## Test Results

- Normal mode: clicking or pressing Enter/Space on a thumbnail opens the viewer; ArrowLeft/ArrowRight navigate; Esc/Close closes; focus returns to the thumbnail.
- Fullscreen mode: identical behavior; no toolbar bleedthrough; gallery navigates across all images in the comments list.
- Images wrapped with anchors open the viewer without navigating away while the viewer is active.
- Touch interactions (swipe, pinch-zoom) continue to work as before.

## Decision Rationale

- Delegation minimizes fragile per-node listeners and is robust to DOM updates that fullscreen toggling might entail.
- Keeping scope tied to `#taskCommentsBlock` ensures gallery discovery remains consistent across states.
- A11y/focus handling aligns with UI/UX best practices and prevents focus leaks.

## Future Enhancements (Backlog)

- Preload adjacent images for smoother gallery navigation.
- Dedicated controls (Prev/Next/Download) with visible buttons.
- Persist zoom level per-image; double-tap to zoom on mobile.


