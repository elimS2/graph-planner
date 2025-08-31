# "Show hidden" initialization bug – roadmap

## Initial Prompt

There is a bug: if I refresh the page and the "Show hidden" setting is active, hidden nodes still do not appear. You have to uncheck this checkbox, then check it again, and only then do the dots (nodes) show up. After reloading the page, the same procedure must be repeated.

=== Analyze the Task and project ===

Deeply analyze our task and our project and decide how to implement this best.

=== Create Roadmap ===

Create a detailed, step-by-step plan of action for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in the plan all the problems, nuances and solutions already discovered and tried, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, update this file and document what has been done, how it was done, what problems occurred and what solutions were taken. For history do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added as tasks – add it to this document. This will help us maintain context, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing in the plan, i.e., what needs to be clicked in the UI.

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## Problem statement

- Symptom: On page reload, with "Show hidden" previously enabled, hidden nodes are not displayed until the checkbox is toggled off and on again.
- Impact: Users cannot rely on persisted visibility settings; extra clicks are required to see hidden nodes after each reload.

## Current behavior and architecture (as of today)

- Frontend: `app/templates/project.html` (single-page template with embedded JS)
  - The function `isShowHiddenEnabled()` currently prioritizes the state of the DOM checkbox `#settingsShowHiddenToggle` and only falls back to `localStorage`:
    - If the checkbox exists, it returns `s.checked`.
    - Otherwise, it checks `localStorage.getItem('showHidden') === '1'`.
  - During initial page init, the graph is fetched via `fetchGraph(...)` before the settings UI is wired and before the checkbox is synchronized with `localStorage`.
  - Result: The checkbox exists in the DOM (unchecked by default), so `isShowHiddenEnabled()` returns `false` even if `localStorage` stores `'1'`. The initial fetch therefore omits `include_hidden=1`, and hidden nodes are not loaded. Only after manually toggling the checkbox (which rewrites the value and refetches) do hidden nodes appear.
- Backend: `app/blueprints/graph/routes.py` `list_nodes`
  - Accepts `include_hidden` query parameter (`{"1","true","yes","y","on"}` → `True`).
  - When `include_hidden` is `False`, it filters nodes (`Node.is_hidden == False`) with a safe fallback for unmigrated DBs.
  - Server logic is correct and already supports this feature; the issue is on the client side initialization order/state.

## Root cause

Initialization order and preference: The initial graph fetch queries `isShowHiddenEnabled()` while the checkbox is present but not yet restored from `localStorage`. Because the function prefers the live checkbox over `localStorage`, it returns `false` and the first fetch omits hidden nodes.

## Options considered

1) Minimal, robust change (preferred):
   - Make `isShowHiddenEnabled()` prefer `localStorage` when a stored value exists. Fall back to the checkbox only if there is no stored value.
   - Pros: Single, isolated change; does not require reordering of init blocks; deterministic with persisted preference.
   - Cons: None significant.

2) Reorder initialization:
   - Wire and restore the `#settingsShowHiddenToggle` from `localStorage` before the first `fetchGraph`. Then the checkbox reflects the persisted value in time for `isShowHiddenEnabled()`.
   - Pros: Behavior aligns with visual state.
   - Cons: Requires moving/wrapping code; touches more of the init sequence.

3) Dual fix (belt-and-suspenders):
   - Apply (1) and also restore the checkbox before the first fetch.
   - Pros: Maximum resilience.
   - Cons: Slightly more code churn than (1) alone.

## Proposed solution

- Implement Option (1):
  - Update `isShowHiddenEnabled()` in `app/templates/project.html` to:
    - If `localStorage.getItem('showHidden')` is `'1'` or `'0'`, return that boolean.
    - Else, read the checkbox state as a fallback.
  - No server changes required.

- Optional hardening (can be a follow-up if desired):
  - In the settings wiring block, set the checkbox initial state from `localStorage` as early as possible in the init flow (before first fetch) to keep UI and data strictly in sync.

## Implementation plan (step-by-step)

1. Update `isShowHiddenEnabled()` to prefer `localStorage` over the DOM state when a saved value is present.
2. Verify `fetchGraph()` appends `include_hidden=1` when `isShowHiddenEnabled()` is true.
3. Manually test on a project with at least one hidden node.
4. Optional: Reorder checkbox restoration to occur before the first fetch for visual consistency at first paint.
5. Code review and merge.

## Manual test checklist

- Setup:
  - Ensure there is at least one node with `is_hidden = true` in the current project.

- Persisted ON state:
  - In the UI, enable "Show hidden" (the toggle in Settings).
  - Reload the page.
  - Expected: Hidden nodes are present immediately; they are styled with lowered opacity and dashed borders; graph includes them without additional toggles.

- Toggle OFF/ON behavior:
  - Turn "Show hidden" off → hidden nodes disappear from the board and from lists.
  - Turn it on again → hidden nodes reappear.

- Persistence across reloads:
  - With "Show hidden" on, reload → still on and nodes visible.
  - With it off, reload → still off and hidden nodes not visible.

- LocalStorage edge cases:
  - Clear `localStorage` entry for `showHidden` and reload → default is OFF, and behavior matches the checkbox state.

- Backend parameter verification:
  - Observe network tab for the `/api/v1/projects/{id}/nodes` request on first load: when ON, it must include `?include_hidden=1` (and language if set).

- Regression checks:
  - Node selection panel correctly reflects per-node `is_hidden` state.
  - Styling selector `node[?is_hidden]` still applies expected visuals.
  - LOD mode and other settings remain unaffected.

## Acceptance criteria

- If `localStorage.showHidden === '1'`, a cold page reload renders hidden nodes immediately without user interaction.
- Toggling the setting still refetches and updates the graph accordingly.
- No backend changes are required.
- No console errors; performance unaffected.

## Risks and mitigations

- Risk: Divergence between `localStorage` and checkbox state if the user changes the checkbox before wiring.
  - Mitigation: The wiring writes `localStorage` on change; the initial read prefers `localStorage`, ensuring deterministic initial fetch. Optionally, restore the checkbox earlier.

## Rollback plan

- Revert the change to `isShowHiddenEnabled()` to restore prior behavior.

## Tasks and status

- [ ] Update `isShowHiddenEnabled()` to prefer `localStorage`.
- [ ] Verify initial fetch includes hidden nodes when expected.
- [ ] Manual testing (all checklist items).
- [ ] Optional: Move checkbox restore earlier in init.
- [ ] Code review.

## Notes / Findings

- Backend endpoint already robustly supports `include_hidden` and has migration-safe fallbacks; no changes needed server-side.

## Changelog

- 2025-08-31: Created roadmap, documented root cause and plan.


