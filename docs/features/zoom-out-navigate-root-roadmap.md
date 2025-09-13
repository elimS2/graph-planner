# Feature Roadmap — Zoom-out Collapse → Navigate to Central Node Link

Last updated (UTC): 2025-09-13T21:36:12.147196+00:00

## Context and Problem Statement

- The board has a “central” node — effectively the most important/heaviest node, from which branches originate.
- Nodes may have an associated `link_url`. When zooming in to an extreme level, we already auto-open the focused node’s link in the current tab (oversized-zoom activation).
- New desired behavior: When zooming out so far that the entire board visually collapses into a single point (i.e., reaches or crosses an extreme min-zoom threshold), automatically “drill up” one level by navigating to the central node’s link (open in current tab), if such a link exists.

## As-Is Overview (Relevant Implementation)

- Frontend lives in `app/templates/project.html` using Cytoscape.js.
- Smooth wheel zoom is implemented with RAF and an anchor (cursor-toward zoom):
  - `cy.userZoomingEnabled(false)` with custom `wheel` handler and `stepZoom()` animating to `targetZoom`.
  - Current zoom bounds enforced in code: roughly `0.05` to `50`.
- LOD (level-of-detail) hides less important nodes at low zoom levels via `applyLOD()`.
- “Oversized zoom → open link” is implemented in `checkAndAutoOpenLinkOnOversized()` and subscribes to `cy.on('zoom', ...)`.
- Nodes include `importance_score` (server-side maintained) and client derives `lod_score` for visibility ranking.
- There is no existing behavior on extreme zoom-out to auto-navigate.

## Definitions

- Central node (for this feature): The single node with the largest descendants count; tie-breakers: degree → importance_score → id. Only nodes with a valid http(s) `link_url` are considered.
- Extreme min-zoom: A rendered zoom level near the existing minimum (e.g., ≤ 0.06–0.08 given min = 0.05). We must avoid false positives while panning/fit.

## Design Goals

- Intuitive: When the board collapses to a “dot,” we exit to the parent context by opening the central node’s link.
- Non-intrusive: No navigation if the central node lacks a `link_url`.
- Predictable: Single-fire per continuous zoom-out gesture (debounced and gated) to avoid repeated navigations.
- Respect performance: O(visible nodes) or O(all nodes) lightweight scans only at rare min-zoom boundary checks.

## Proposed UX and Behavior

- Trigger condition: On `cy.on('zoom', ...)`, if `cy.zoom()` transitions below `MIN_NAVIGATE_LEVEL` and was previously above it within a short window, consider navigation.
- Candidate resolution:
  1) Build a candidate list from currently available nodes (prefer visible base nodes; if empty, fallback to all nodes).
  2) Rank by (a) descendants, then (b) degree, then (c) importance_score, then (d) id.
  3) Pick the top candidate; verify its `link_url` is a valid http(s) URL.
- Navigation:
  - Open in current tab via `location.assign(url)` (consistent with oversized-zoom behavior override).
- Gating & safety:
  - Debounce and once-per-session-window gating using a timestamp (e.g., `zoomOutNavigateFiredAt`).
  - Suppress when the board is actively “fitting” (e.g., immediately after `cy.fit()`) via a short cool-down window.
  - Require a “collapsing” gesture: track recent wheel direction and ensure net zoom delta indicates zooming out.
  - Respect a user preference: `localStorage['zoom.minCollapseNavigate.enabled']` (default on). A Settings toggle has been added.

## Technical Plan (Step-by-Step)

1) Add a feature flag and thresholds
- Constants in the script:
  - `MIN_NAVIGATE_LEVEL = 0.06` (tuneable; must be > min zoom 0.05)
  - `COLLAPSE_WINDOW_MS = 600` (time window to consider it one zoom-out gesture)
  - `FIT_COOLDOWN_MS = 600` (suppress immediately after `cy.fit()` or `showAllAndFit()`)
  - `ENABLE_KEY = 'zoom.minCollapseNavigate.enabled'` (default enabled unless set to '0')

2) Track zoom direction and gesture windows
- Maintain `lastZoomLevel`, `lastZoomAt`, `lastWheelAt` (already present), and `lastFitAt`.
- On wheel down (zoom-out), record gesture recency.

3) Implement central node selection
- Prefer base visible nodes (not children of collapsed groups, `display !== 'none'`). If none, fallback to all nodes.
- Compute degree using existing adjacency or quick pass over edges.
- Comparator: descendants desc → degree desc → importance_score desc → id asc.

4) Navigation handler at min zoom
- Subscribe via `cy.on('zoom', handleZoomOutNavigate)`.
- Checks: feature flag, cooldown, recent interaction, threshold crossing downward, once-per-gesture gating.
- If passes, navigate with `location.assign(url)`.

5) Settings UI and persistence
- Toggle added in Settings → Zoom: “Navigate to central node on extreme zoom-out”.
- Persisted in `localStorage[ENABLE_KEY]` (default enabled).

6) Accessibility and keyboard
- Button-based zoom out behaves the same.

7) Telemetry (optional)
- Dev-only console logs for tuning.

## Manual Test Plan

1) Happy path — central node with link
- Ensure a node with max descendants has a valid `http(s)` link.
- Zoom out continuously until collapse; expect navigation to its link (once).

2) No link on central node
- Make the top descendants node have no `link_url`. Zoom out to collapse. Expect: no navigation.

3) Fit cooldown
- Click “Fit” or “Reset View”, then immediately zoom out to minimum. Expect: no navigation within cooldown.

4) Tie-breaking
- Prepare two nodes with equal descendants; ensure differing degree/importance. Expect correct tie-break.

5) Visibility fallback
- With filters/LOD hiding many nodes, still resolve from all base nodes if visible is empty.

6) Button zoom-out
- Use the Zoom Out button repeatedly: same behavior.

7) Toggle off
- Disable in Settings → Zoom. Expect: no navigation.

## Risks and Mitigations

- False positives near fit: mitigated by cooldown and interaction check.
- Unintended navigation: require clear threshold crossing and zoom-out direction.
- Performance: compute ranking only on trigger and on small subset if possible.
- Definition ambiguity: documented; could be made configurable later.

## References (Code Pointers)

- Oversized zoom auto-open:
  - `checkAndAutoOpenLinkOnOversized()` in `app/templates/project.html` around lines ~2746–2809.
- LOD and degree/descendants estimation: `applyLOD()` region (~2493–2583) in `project.html`.
- Smooth zoom and wheel handler: region (~3183–3211) in `project.html`.
- Node model fields: `importance_score`, `link_url`, `link_open_in_new_tab` in `app/models/__init__.py`.

## Initial Prompt (English Translation)

"""
We have a central point on the board, i.e., the one with the largest weight, because branches start from it.

Also, points can specify a link; if we zoom in to the maximum on a point, we kind of navigate to the link either in a new tab or in the current one depending on the link setting.

So I want this: if we zoom out our board so that everything converges into a single point, then we drill up one level. That is, navigate to the link specified for the largest point on the map. The central one, from which the branches begin.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a `docs/features` folder for this. If such a folder does not exist, create it. Document in as much detail as possible all discovered and tried problems, nuances and solutions, if any. As you progress in implementing this task, you will use this file as a to-do checklist; you will update this file and document what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; only update their status and add comments. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve context, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and in the project text. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.
"""

## Implementation Checklist

- [x] Add constants and storage key; default enabled.
- [x] Track zoom direction, last zoom level, wheel/button recency, and fit cooldown.
- [x] Implement central node resolver using descendants → degree → importance → id.
- [x] Add `handleZoomOutNavigate` and subscribe on `cy.on('zoom', ...)`.
- [x] Open `location.assign(url)` once per gesture when threshold crossed.
- [x] Add Settings toggle in Zoom section and persist to `localStorage`.
- [ ] Manual QA scenarios executed and thresholds tuned.
- [ ] Update docs and changelog after release.
