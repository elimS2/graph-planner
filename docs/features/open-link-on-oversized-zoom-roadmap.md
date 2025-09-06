# Feature Roadmap — Auto-open Node Link when Node Exceeds Viewport on Zoom

## Context and Problem Statement

When zooming the graph, if a node becomes larger than the viewport and that node has a link, the link should be opened in the current browser tab, even if the node’s link preference or global setting says to open in a new tab.

The intent is to turn an extreme zoom-in on a node into a strong “activation” signal to open its associated link in-place.

## Current Behavior (As-Is)

- Frontend stack: Cytoscape.js, custom smooth wheel zoom, LOD logic.
- Zoom logic and LOD:
  - LOD registered on `cy.on('zoom', applyLOD)`.
  - Custom wheel zoom implemented via RAF and anchoring to cursor: see `stepZoom()` and `cyContainer.addEventListener('wheel', ...)`.
  - References in `app/templates/project.html`:

```
1398:1463:app/templates/project.html
// LOD: zoom-aware visibility using lod_score ...
cy.on('zoom', applyLOD);
applyLOD();

1755:1783:app/templates/project.html
// Zoom controls with smooth animation and wheel handler
function stepZoom() { ... }
cyContainer.addEventListener('wheel', (e) => { ... }, { passive: false });
```

- Node linking behavior:
  - Each node may have `data.link_url` and `data.link_open_in_new_tab`.
  - Ctrl+click opens `link_url` in either `_blank` or `_self` depending on preferences:

```
845:860:app/templates/project.html
// Ctrl+click opens link_url in new tab (if present)
if (oe && oe.ctrlKey && url) {
  let openNew = (localStorage.getItem('openLinkInNewTab') !== '0');
  const nodePref = evt.target.data('link_open_in_new_tab');
  if (typeof nodePref === 'boolean') openNew = nodePref;
  const target = openNew ? '_blank' : '_self';
  window.open(url, target, openNew ? 'noopener,noreferrer' : undefined);
  return;
}
```

- Selection: `selectedNodeId` is set on node tap and is used widely to reflect UI state in the Task Panel.

## Goal (To-Be)

- When the user zooms such that the selected node’s rendered size becomes larger than the viewport (width or height), and the node has a valid `link_url`, automatically open that link in the current tab (override any “open in new tab” setting).
- Trigger only once per node per session/selection to prevent repeated or looped navigation.

## Non-Goals

- Do not change Ctrl+click behavior.
- Do not add per-node or global UI settings unless clearly needed by UX feedback.
- Do not open links for unselected nodes or for nodes without a link.

## Principles and Constraints

- Apply SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code practices.
- UI/UX: Avoid surprises and loops; provide predictable behavior, good performance, no flicker.
- Security: We already sanitize/validate URLs server-side. Continue to rely on that.
- Reliability: Prevent multiple openings on small zoom deltas. Use a threshold-crossing approach.

## Proposed Behavior and Algorithm

Definitions:
- Viewport size: `vpW = cy.width()`, `vpH = cy.height()`.
- Node box: `box = node.renderedBoundingBox()` → use `box.w`, `box.h`.
- Oversized condition: `box.w >= vpW` OR `box.h >= vpH` (strict). To reduce accidental triggers, we can add a small margin factor like `0.95`.

Trigger rule:
- If `selectedNodeId` exists, the corresponding node exists in the graph, and the node has a non-empty `link_url`.
- On any zoom update (including wheel-based animation frames that call `cy.zoom()`), compute the oversized condition.
- Detect rising edge: the moment the condition transitions from false to true for this node, open `link_url` in the current tab and mark it as fired to avoid re-entry.

Once-only semantics:
- Maintain `oversizedOpenFiredForNodeIds: Set<string>`.
- Clear the fired flag when selection changes (new `selectedNodeId`).
- Optional: Clear on navigation back/reload naturally.

Open in current tab:
- Use `location.assign(url)` to avoid popup blockers and guarantee same-tab navigation (more robust than `window.open(url, '_self')`).
- Explicitly ignore `link_open_in_new_tab` preference for this auto-trigger path.

Hysteresis and safety:
- Use a threshold factor `TH = 0.98` (i.e., 98% of viewport) to reduce noisy toggling around equality.
- Only act on rising edge (below→above). No action on above→below.

## Implementation Plan (Step-by-Step)

1) Wire oversized detection on zoom
   - Add a new function `checkAndAutoOpenLinkOnOversized()` and subscribe it to `cy.on('zoom', ...)` alongside LOD.
   - The function should be short and focused; reuse existing globals (`selectedNodeId`, `cy`).

2) Compute node and viewport bounds
   - Guard: if no `selectedNodeId`, return.
   - Retrieve the node via `cy.getElementById(String(selectedNodeId))`; guard if empty.
   - Read `link_url` and return if missing/empty.
   - Compute `vpW`, `vpH`, and node `box`.

3) Rising-edge detection and once-only gating
   - Keep `let oversizedState = false;` per currently selected node, or use a `Map<string, boolean>`.
   - When transitioning from `false` to `true` and not yet fired for this node, call `location.assign(url)` and add the node id to `oversizedOpenFiredForNodeIds`.
   - Reset per-node state when `selectedNodeId` changes (in the existing node tap handler).

4) Override target behavior
   - Always open in the current tab for this path; do not consult `link_open_in_new_tab` or localStorage.

5) Logging and resilience
   - Optionally `console.log` a concise trace (can be removed in production) to ease verification.
   - Wrap calls in try/catch to avoid breaking zoom.

6) Documentation and tests
   - Update this roadmap checklist.
   - Add manual test steps (below) and execute them.

## Manual Test Plan (What to click)

1) Basic oversized open
- Select a node that has a `link_url` (e.g., `https://example.com`).
- Zoom in until the node’s rendered size exceeds the viewport.
- Expected: The link opens in the current tab exactly once at the threshold crossing.

2) Respect override to current tab
- Ensure the node’s `link_open_in_new_tab` is true.
- Zoom in to oversize.
- Expected: The link still opens in the current tab (override works).

3) No link → no action
- Select a node with no `link_url`.
- Zoom in aggressively.
- Expected: No navigation.

4) Repeat prevention
- With a linked node, cross the threshold once (link opens).
- Navigate back to the app (or re-open it), select the same node again, and zoom to oversize.
- Expected: Opens only once per selection session; does not loop on small zoom oscillations.

5) Selection change reset
- Trigger the oversized open for Node A.
- Select Node B (with `link_url`) and zoom to oversize.
- Expected: Node B triggers its own open once; Node A does not reopen without reselecting.

6) Ctrl+click remains unaffected
- Select a linked node, do not zoom to oversize.
- Ctrl+click the node.
- Expected: Opens per the checkbox/per-node preference (unchanged), typically in a new tab if enabled.

7) Performance/UX
- On large graphs, zoom in-and-out quickly.
- Expected: No noticeable lag or jank; no accidental opens when no node is selected or no link is set.

## Edge Cases

- Very large labels or groups: oversized should still compute from rendered bounding box.
- Hidden nodes or nodes outside viewport: we act only for the selected node; if it is hidden, the box size will not exceed viewport; the guard will prevent accidental opens.
- Non-http schemes (`mailto`, `ftp`) are already validated server-side; navigation with `location.assign` should still work.
- Popup blockers: using `location.assign` avoids the blocker for programmatic navigations.

## Risks and Mitigations

- Risk: Unintended navigation during exploratory zooming.
  - Mitigation: Trigger only for the selected node and only once on rising edge beyond a near-full-screen threshold (e.g., 98%).
- Risk: Users may want to disable this behavior.
  - Mitigation: Start without UI toggles (KISS). If feedback indicates the need, add a settings toggle later.
- Risk: Precision differences across devices.
  - Mitigation: Use a margin factor (e.g., `0.98`) to reduce sensitivity to rounding.

## Initial Prompt (English Translation)

I want to make it so that during zoom, when a node becomes larger than the screen size and if this node has a link, this link opens in the current tab, even if the link’s properties specify opening in a new tab.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a `docs/features` folder for this. If such a folder does not exist, create it. Document in as much detail as possible all discovered and tried problems, nuances, and solutions if any. As you progress in implementing this task, you will use this file as a to-do checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and add comments. If, during implementation, it becomes clear that something needs to be added to the tasks—add it to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and in the project text. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

## Implementation Checklist

- [x] Add `checkAndAutoOpenLinkOnOversized()` function with viewport and box calculations.
- [x] Subscribe it to `cy.on('zoom', ...)` alongside existing LOD call.
- [x] Maintain rising-edge and once-only gating (`oversizedOpenFiredForNodeIds`).
- [x] Reset gating on selection change.
- [x] Force same-tab navigation via `location.assign(url)`.
- [x] Light logging for verification; toggle via `localStorage.setItem('oversizeDebug','1')`.
- [x] Manual test pass (initial scenarios).
- [x] Auto-focus detection (without click): choose focus node under viewport center, ranked by size and proximity.
- [x] Increase max zoom to 50 and adjust near-max threshold accordingly (47.5).
- [x] Early prewarm near threshold: `dns-prefetch` + `preconnect` + `rel=prefetch`.
- [x] Speculation Rules: dynamic `script type="speculationrules"` with prefetch for any origin, prerender for same-origin near-likely navigation.
- [x] Reset auto-open state on `pageshow` (BFCache back/forward) and refresh speculation caches.

Remaining / Next:
- [ ] Settings toggles (UI): enable/disable auto-open on oversize; enable/disable prefetch/prerender.
- [ ] Cap and eviction for speculation lists (limit concurrent prerenders; simple LRU).
- [ ] Make thresholds configurable (prewarm ratio, prerender ratio, primary ratio, near-max level).
- [ ] Browser support notice and graceful fallback for Speculation Rules; optional `preload` for critical same-origin assets.
- [ ] Automated tests: unit and E2E for oversize detection, focus without click, BFCache `pageshow` reset.
- [ ] Telemetry hooks (optional): counters for prewarm/prerender and actual navigations.
- [ ] Accessibility review: keyboard-only path and discoverability notes.

## Changelog (2025-09-06)

- Implemented oversize auto-open with once-only gating and selection reset.
- Added focus node detection to work without prior click.
- Increased maximum zoom to 50; tuned near-max threshold to 47.5.
- Added debug logs guarded by `oversizeDebug` localStorage flag.
- Added early prewarm (dns-prefetch, preconnect, prefetch) at ~40% viewport or near-max zoom.
- Integrated Speculation Rules: prefetch for any origin; prerender for same-origin when node is very likely to be opened (~80% viewport, primary trigger, or near-max).
- Added `pageshow` handler to clear state after Back/Forward and refresh speculation lists.

## References (Code Pointers)

- Zoom/LOD:
  - `app/templates/project.html` — near lines 1398–1463, 1755–1783
- Node link open on Ctrl+click:
  - `app/templates/project.html` — near lines 845–860
- Node data provisioning (`link_url`, `link_open_in_new_tab`):
  - `app/templates/project.html` — near lines 564–570
  - Backend schema/model already include `link_url` and `link_open_in_new_tab`.

## Notes

- Keep names and code comments in English.
- Keep the implementation focused and minimal to reduce risk (KISS) and preserve performance.


