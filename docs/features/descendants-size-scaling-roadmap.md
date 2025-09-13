# Descendants-based Node Size – Scaling Improvements Roadmap

Created: 2025-09-13T09:22:09Z (UTC)

## Initial Prompt (translated from Russian)

"On the board, our dots differ in size depending on the number of descendant dots. But at certain sizes the difference is not visible; for example, nodes with Descendants (via edges) 40, 18, and 158 will have the same size. Can this be improved? Think about best practices in such cases.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how to best implement this.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Record in as much detail as possible all identified and tried problems, nuances, and solutions, if any. As you progress in implementing this task, you will use this file as a to-do checklist, updating this file and documenting what has been done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and comment. If during the implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us maintain the context window, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project captions.

When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt you wrote in the plan, but translate it into English. You can name it in the document-plan something like "Initial Prompt". This is necessary to preserve the context of the task statement in our roadmap file as accurately as possible without any "broken telephone" effect.

Also include steps for manual testing, that is, what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.

Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.

Use Best Practices.

==================================================

=== Get time from MCP Server ===

If you need the current time, get it from the time MCP Server."

## Context and Current Behavior

- Frontend template: `app/templates/project.html` renders Cytoscape graph.
- Node size is currently driven directly from `data(descendants)` via a static linear mapping:
  - Style rule: width/height = `mapData(descendants, 0, 20, 20, 80)`.
  - Consequence:
    - Any `descendants >= 20` clamp to 80px (max), so values 40 and 158 look identical.
    - Values close to 20 (e.g., 18) may appear visually similar to 20 due to small pixel delta and label/border dominance.
- Client computes descendants per node on load and on edge mutations:
  - Elements building computes `n.data.descendants = countDesc(n.data.id)`.
  - On add/remove edge we recompute descendants and update data.
- A lightweight LOD score also uses normalized descendants, but does not affect size.

## Problem Statement

Current static mapping saturates for many real-world graphs with long tails. Large counts lose differentiation, and near-cap values look too similar, harming visual ranking. We need a perceptually sane, robust scaling that:

- Preserves differentiation across orders of magnitude.
- Is robust to outliers.
- Remains legible and clickable at all zoom levels.
- Performs well on N+E recomputations.

## Design Options (Best Practices)

1) Dynamic linear scaling (min/max from data)
- Map `[minDesc, refMax] → [minPx, maxPx]`, where `refMax` is `maxDesc` or a robust cap (p95).
- Pros: simple, predictable. Cons: still sensitive to outliers if not capped.

2) Logarithmic scaling (perceptual)
- `size = minPx + (maxPx - minPx) * log1p(d) / log1p(refMax)` using `refMax = maxDesc or p95`.
- Pros: preserves differences across large ranges; widely used in network viz.
- Cons: very low counts may look compressed unless minPx is sufficient.

3) Square-root scaling (area proportionality)
- `size ∝ sqrt(d)` ensures perceived area roughly follows count.
- Pros: good perceptual match for area encoding. Cons: still needs cap handling.

4) Quantile/bucketed scaling
- Divide counts into k-quantiles (e.g., 5) and map to discrete sizes.
- Pros: stable, easy to read legend. Cons: less fine-grained within buckets.

5) Secondary encodings (for ties/saturation)
- Color lightness or saturation by normalized descendants.
- Border width accent for top decile.
- A tiny numeric badge at higher zooms with exact descendants.
- Pros: multi-channel clarity, better accessibility. Cons: more UI complexity.

Recommendation: Default to log1p scaling with robust cap at p95 and allow user override between Linear / Log / Quantile via Settings. Keep a generous min size for clickability and a moderate max to avoid label collisions.

## Proposed Defaults

- `method`: logarithmic (log1p).
- `reference`: p95 of descendants distribution (fall back to max if few nodes).
- `minPx`: 20 (click target baseline aligns with current min 20).
- `maxPx`: 72 (slightly below current 80 to reduce label crowding).
- `legend`: optional toggle to show size legend.

## Implementation Plan (KISS, DRY, SoC)

1. Compute visualization size per node (single source of truth)
- In the `toElements(graph)` pipeline (in `project.html`), after computing `descendants`, compute:
  - `descArray` of counts, determine `refMax` as p95 (or max if N < 20).
  - `viz_size` per node using selected `method` and `[minPx, maxPx]`.
- Store `viz_size` in `n.data.viz_size`.

2. Use `viz_size` in Cytoscape style
- Replace `mapData(descendants, 0, 20, 20, 80)` with `'data(viz_size)'` for both `width` and `height`.
- Keep `descendants` for logic (LOD, analytics), but decouple size from static mapping.

3. Settings UI (non-blocking enhancements)
- In the Settings panel, add "Node Size by Descendants" block with:
  - Method: radio group (Linear, Log, Quantile).
  - Reference: (Max, p95).
  - Range: min and max sliders with sensible bounds (12–96px) and live preview.
  - Reset to defaults button.
- Persist choices to `localStorage`; recompute `viz_size` on change.

4. Optional secondary channel
- Add border width bump for top decile or color ramp for normalized descendants (color-blind safe palette).
- A tiny badge with numeric value at zoom > threshold to aid exact reading.

5. Update on graph mutations
- On edge add/remove, recompute `descendants`, recompute `viz_size` for all nodes using current settings, batch-update node data.
- Ensure O(N+E) behavior as today; avoid per-node DOM reads; use pure data transforms.

6. Telemetry & debug (optional)
- Console-guarded summary of distribution (min/median/p95/max) to validate mapping during development (disabled in production builds).

## Acceptance Criteria

- Nodes with descendants 18, 40, 158 produce visibly different sizes under default settings.
- Large counts no longer collapse to a common max, unless they are beyond p99 (intentional with cap).
- User can switch between Linear/Log/Quantile and see immediate updates without reload.
- Minimum node size remains comfortably clickable; labels do not overflow excessively.
- No linter errors or performance regressions on typical project sizes.

## Manual Test Plan (UI steps)

1. Open any project with varied branching (at least one node with > 50 descendants).
2. Observe default sizing differences among nodes with descendants ≈ 5, 18, 40, 158.
3. Open Settings → "Node Size by Descendants".
   - Switch Method to Linear and confirm visual change; switch back to Log.
   - Change Range min/max and confirm sizes update live.
   - Toggle Reference between Max and p95; ensure outlier impact changes as expected.
4. Add a new edge to create additional descendants for a selected node.
   - Expect size and sidebar counters to update consistently.
5. Remove the edge; sizes revert accordingly.
6. Zoom in; if badge is enabled, verify numeric visibility and contrast.
7. Reload page; verify persisted settings are applied.

## Work Items and Status

- [ ] Compute `viz_size` per node in `toElements` with chosen defaults (Log + p95).
- [ ] Replace static `mapData` with `data(viz_size)` for width/height.
- [ ] Recompute `viz_size` on edge add/remove.
- [ ] Implement Settings controls (method, reference, range) with persistence.
- [ ] (Optional) Secondary encoding (border/colour) and zoom-based numeric badge.
- [ ] Add a small legend toggle.
- [ ] Manual QA per test plan and adjust defaults if needed.
- [ ] Document outcomes and any tuning decisions here.

## Risks & Mitigations

- Outlier-heavy graphs could still compress mid-range: use p95 cap and user-adjustable max.
- Visual clutter at high sizes: keep `maxPx` moderate and offer quantile mode.
- Performance on very large graphs: reuse existing O(N+E) passes; avoid per-element reflows.
- Accessibility: ensure minimum size and sufficient color contrast; test color-blind palettes.

## Notes

- All code and UI texts remain in English per project rules.
- Implementation should follow SOLID, DRY, KISS, Separation of Concerns, and Clean Code practices.

## Appendix: Mapping Formulas

Let \( d \) be descendants, and \( R \) the reference maximum (max or p95).

- Linear: `t = clamp(d / R, 0, 1)`; `size = minPx + (maxPx - minPx) * t`.
- Log: `t = clamp(log1p(d) / log1p(R), 0, 1)`; `size = minPx + (maxPx - minPx) * t`.
- Sqrt: `t = clamp(sqrt(d) / sqrt(R), 0, 1)`; `size = minPx + (maxPx - minPx) * t`.
- Quantile (k buckets): compute thresholds; map to k evenly spaced sizes between minPx and maxPx.

## Changelog

- 2025-09-13: Drafted roadmap and proposed defaults and plan.


