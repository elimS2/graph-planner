# Focus vs. Zoom Link — Anchor-First Precedence Roadmap

## Context and User Symptom
- When a node is already selected (focused) and the user zooms toward another node that has a `link_url`, the existing selection prevents auto-navigation to the zoomed node’s link. The zoom action intends to activate the node under the zoom anchor (cursor), but the logic prefers the selected node instead.

## Current Behavior (As-Is)
- Frontend uses Cytoscape.js with custom smooth wheel zoom anchored to the cursor.
- Auto-open-on-oversize is handled in `app/templates/project.html` by `checkAndAutoOpenLinkOnOversized()`.
- Selection precedence today:
  - If `selectedNodeId` is set, it is always used for oversize checks.
  - Only if there is no selection, fallback node is derived by `findNodeByAnchor()`.
- Code pointers:
  - Anchor tracking and wheel zoom:
    - `stepZoom()`, `cyContainer.addEventListener('wheel', ...)`, and `anchor` updates.
  - Fallback focus search when nothing is selected:
    - `findNodeByAnchor()` uses cursor-anchored heuristic (containment → nearest within radius; visible nodes with `link_url`).
  - Oversize auto-open logic (simplified):
    - `checkAndAutoOpenLinkOnOversized()` chooses `selectedNodeId` first; if falsy, uses `findNodeByAnchor()`; checks node’s rendered box vs viewport; then `location.assign(url)`.

## Root Cause
- The decision order inside `checkAndAutoOpenLinkOnOversized()` prioritizes the selected node over the zoom anchor. Thus, even if the user is zooming toward a different node (under the cursor), the system continues to evaluate the selected node and may open the wrong link or block opening the intended one.

## Goal (To-Be)
- When zoom is driven by the cursor (mouse wheel), the node under the zoom anchor should take precedence over the currently selected node for oversize navigation.
- Preserve intuitive behavior for non-cursor zoom (e.g., toolbar buttons or keyboard): if there is a selection, use it; otherwise use viewport center or the fallback heuristic.

## Design Principles
- Anchor-first on wheel-driven zoom.
- Selection-first on non-wheel zoom, for consistency and predictability.
- Do not navigate unless the anchor actually targets a node with a `link_url` (containment or proximity within a safe pixel radius).
- Keep performance smooth; avoid heavy scans per frame.
- Minimal invasive change; keep existing thresholds and safeguards.

## Proposed Decision Tree
1) Determine zoom origin (wheel vs. non-wheel):
   - Track `lastWheelAt` timestamp in the wheel handler.
   - If `Date.now() - lastWheelAt <= WHEEL_WINDOW_MS` (e.g., 400ms), treat current zoom as wheel-driven.
2) If wheel-driven:
   - Compute `anchorCandidate = findNodeByAnchor()`.
   - If `anchorCandidate` exists:
     - Use `anchorCandidate` for oversize checks and navigation, regardless of `selectedNodeId`.
   - Else:
     - Fallback to `selectedNodeId` if present; otherwise do nothing.
3) If not wheel-driven:
   - If `selectedNodeId` exists, use it.
   - Else use `findNodeByAnchor()` (which will effectively use viewport center when no anchor precision is available) or do nothing if it returns null.

## Implementation Plan (Step-by-Step)
1) Introduce wheel-origin gating
   - Add `let lastWheelAt = 0;` near existing `anchor` definition in `app/templates/project.html`.
   - In the wheel handler, set `lastWheelAt = Date.now();`.
   - Define `const WHEEL_WINDOW_MS = 400;` near other constants in the zoom block.

2) Reorder precedence in `checkAndAutoOpenLinkOnOversized()`
   - Compute `const isWheelZoom = (Date.now() - lastWheelAt) <= WHEEL_WINDOW_MS;`.
   - If `isWheelZoom`:
     - Try `idToCheck = findNodeByAnchor();` and use it if truthy.
     - If falsy, fallback to `selectedNodeId`.
   - Else (non-wheel zoom):
     - Keep current selection-first behavior (selected → anchor fallback).

3) Keep thresholds and once-only gating intact
   - Preserve: `RATIO_TH_PRIMARY`, `RATIO_TH_SECONDARY`, `MAX_ZOOM_OPEN_LEVEL`.
   - Preserve `oversizedOpenFiredForNodeIds` dedup semantics.

4) Add a runtime toggle (opt-out) via localStorage
   - Key: `zoom.anchorPrecedence.enabled` (default on).
   - Wrap the new precedence with a guard; if the key is explicitly `'0'`, revert to current selection-first behavior always.

5) Inline documentation and clarity
   - Add concise comments explaining why anchor-first is applied during wheel-driven zoom.
   - Keep comments in English and match existing formatting.

## Acceptance Criteria
- Zooming with the mouse wheel toward a linked node while another node is selected opens the intended node’s link when the node becomes oversized.
- Using toolbar zoom buttons while a node is selected keeps selection-first behavior.
- When nothing is selected, zooming toward a linked node behaves as today (but now consistently anchor-first).
- Performance remains smooth on large graphs.
- Ctrl+Click behavior remains unchanged.

## Manual Test Plan (UI steps)
1) Repro baseline
   - Select node A (has a link). Move cursor over node B (also has a link). Wheel-zoom toward B.
   - Expected: B’s link opens when B becomes oversized; A’s selection does not block it.
2) No selection scenario
   - Reload the page, do not select any node. Place cursor over a linked node C and wheel-zoom in.
   - Expected: C’s link opens when oversized; no other node’s link opens.
3) Button zoom with selection
   - Select node D (linked). Click Zoom In button until oversized.
   - Expected: D’s link opens (selection-first for non-wheel zoom).
4) Button zoom without selection
   - No node selected. Click Zoom In button; ensure no spurious navigation occurs unless a node under viewport center is oversized.
   - Expected: If a node centered becomes oversized and has a link, it opens; otherwise no navigation.
5) Mixed interactions
   - Select node E. Start with button zoom (no open yet), then move the cursor over F and use wheel zoom.
   - Expected: Anchor-first applies and F opens when oversized.
6) Edge cases
   - Linked node hidden due to LOD at low zoom: ensure navigation only happens after it becomes visible and oversized.
   - Very fast wheel bursts: behavior remains stable; only one navigation fires per node due to dedup.

## Risks and Mitigations
- Risk: Misclassification of zoom origin when switching quickly between inputs.
  - Mitigation: Reasonable `WHEEL_WINDOW_MS` and stable dedup set prevent flapping.
- Risk: Unexpected behavior for users who rely on selection-first at all times.
  - Mitigation: Runtime toggle via localStorage to revert to legacy precedence.

## Telemetry / Debug Aids
- Keep existing `oversizeDebug` logs.
- Optionally log the chosen `idToCheck` and whether wheel gating applied when `oversizeDebug` is on.

## Status Checklist (living)
- [x] Add `lastWheelAt` and gating constant
- [x] Reorder precedence in `checkAndAutoOpenLinkOnOversized()`
- [x] Add localStorage feature flag
- [ ] Manual test pass (all scenarios)
- [ ] Update docs with results and decisions

## Initial Prompt (English)
Translated (en):
> If a node is focused and we zoom on another node with a link, then the focus interferes with the zoom-based navigation to that link.
>
> === Analyse the Task and project ===
>
> Deeply analyze our task and project and decide how best to implement this.
>
> ==================================================
>
> === Create Roadmap ===
>
> Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a `docs/features` folder for this. If there is no such folder, create it. Capture in the document, as thoroughly as possible, all issues already discovered and tried, nuances and solutions if any. As you progress with the implementation, you will use this file as a to-do checklist, updating it and documenting what was done, how it was done, what issues arose and what decisions were made. For history, do not delete items; you can only update their status and comment. If during implementation you realize something should be added as tasks—add it to this document. This will help us preserve the context window, remember what we already did, and not forget planned items. Remember that only the English language is allowed in code and comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs adjusting in it.
>
> Include this prompt (that I wrote) in the plan itself, but translate it into English. You can call it something like "Initial Prompt" in the plan-document. This is needed to preserve the exact task context in the roadmap file without the "broken telephone" effect.
>
> Also include manual testing steps, i.e., what to click through in the UI.
>
> ==================================================
>
> === SOLID, DRY, KISS, UI/UX, etc ===
>
> Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.
