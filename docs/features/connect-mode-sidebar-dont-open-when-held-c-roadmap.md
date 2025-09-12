Title: Prevent sidebar auto-open while holding C (Connect mode)

Status: Draft

Owner: Frontend

Created: 2025-09-12

Initial Prompt

In our app, you can connect nodes on the board by holding the C key. When the C key is held, I want the sidebar to NOT open if it is closed.

Additionally, please:
- Deeply analyze the task and the project and decide how to best implement this.
- Create a detailed, step-by-step roadmap in a separate document under docs/features. If the folder doesn’t exist, create it. Document any problems, nuances, and solutions as they arise. Use this file as a to-do checklist: keep history by updating status/comments, not deleting items. If new sub-tasks emerge, add them here.
- Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
- Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
- If you need the current time, obtain it from the time MCP Server.

Background & Current Behavior

- The board is implemented in app/templates/project.html with Cytoscape.js.
- Connect mode exists; it can be activated via the “+ Edge” button or by holding the C key. Code location (approx.): connectMode IIFE around the 1810–1860 lines.
- Sidebar visibility is controlled via localStorage key `sidebarHidden` and helper `applySidebarVisibility()`. The sidebar can auto-reveal on node tap when hidden (wireRevealSidebarOnNodeTap). Code location (approx.): 2306–2337 and 2707–2772.
- Auto-hide/reveal scheduler is exposed on window.sidebarAutoHide with schedule/cancel.
- Problem: When holding C to quickly connect nodes, a node tap may trigger the auto-reveal behavior even if the user intends to stay in connect mode and keep the canvas full-width.

Goal

- When connect mode is active due to holding the C key, prevent the sidebar from opening as a result of node taps or edge cases (auto-reveal, hot-zone reveal, etc.). The sidebar must remain hidden while the key is held down.

Non-Goals

- Do not remove normal toggle behavior via the sidebar button.
- Do not change explicit user actions to open the sidebar (e.g., pressing the toggle button) outside of connect-mode hold.

Constraints & Principles

- KISS: minimal, targeted changes around existing helpers.
- DRY: reuse connect mode state; avoid duplicating logic.
- SoC: do not entangle sidebar logic with Cytoscape rendering beyond necessary checks.
- Accessibility: no keyboard conflicts; keep ESC to cancel connect; ensure focusable elements still work.

Proposed Approach

1) Introduce a global, read-only accessor for connect-mode state.
   - Extend the connectMode IIFE to set `window.isConnectModeActive` boolean.
   - It should reflect the transient hold (keydown C -> true; keyup C -> false; also true when activated via "+ Edge" button until cancelled).

2) Guard sidebar auto-reveal logic.
   - In wireRevealSidebarOnNodeTap, before auto-revealing, check `window.isConnectModeActive`. If true, skip reveal.
   - Likewise, for any hot-zone or auto-hide restore that may trigger reveal while the user is holding C, ensure a similar guard is placed or centralized in applySidebarVisibility trigger points.

3) Optional: Temporary suppression flag.
   - As a defensive measure, add a short-lived suppression flag `window.sidebarRevealSuppressed` that is toggled on connect-mode activation and cleared on cancel. Auto-reveal handlers honor this flag.

4) Persist nothing.
   - Do not store the active state in localStorage/sessionStorage; it is a runtime-only state.

5) Tests (manual) and quick scripts (if needed).

Detailed Steps

- Step A: Add connect-mode state exposure.
  - Inside the connectMode IIFE, on setActive(true) set `window.isConnectModeActive = true` and on cancel() set it to false.
  - For keydown/keyup (C), ensure the state mirrors the key hold lifecycle.

- Step B: Update reveal-on-tap handler.
  - In wireRevealSidebarOnNodeTap, early-return if `window.isConnectModeActive` is true.

- Step C: Verify other reveal paths.
  - If there is a right-edge hot-zone auto-reveal path, add a guard there as well (skip when connect mode is active). If not found, ensure `restoreFromAutoHide()` is not called while connect mode is active.

- Step D: UX polish.
  - No flashes: ensure no `setTimeout` queued reveal executes after connect mode activates. Cancel timers if necessary.
  - Cursor crosshair remains unchanged.

- Step E: Manual testing.

Manual Test Plan

Prereqs:
- Sidebar initially hidden (localStorage `sidebarHidden` = '1').
- Graph loaded with at least two nodes.

Tests:
- T1: Hold C, click a node, then another node to connect. Expected: sidebar stays hidden the entire time.
- T2: While holding C, click a node only once, wait 2–3s. Expected: no auto-reveal occurs.
- T3: Release C; click a node. Expected: auto-reveal (existing behavior) works again.
- T4: Press "+ Edge" button to activate connect mode (without holding C); click nodes. Expected: keep sidebar hidden until connect mode cancels; then normal behavior resumes.
- T5: While holding C, move cursor to right-edge hot zone (if enabled). Expected: no sidebar reveal.
- T6: With sidebar visible, hold C and try to toggle via button. Expected: button still works (explicit user action wins). After connect completes/cancels, behavior remains consistent.
- T7: Regression: other keyboard shortcuts (N/E/F/Delete) unaffected.

Edge Cases & Risks

- If a reveal timer was already scheduled before connect mode activation, it might fire. Mitigation: cancel auto-hide timers when connect mode activates (optional), or check active state right before reveal.
- IME or different keyboard layouts: isConnectKey already checks both Latin 'c' and Cyrillic 'с'.
- Editable fields: global key handlers skip when focused on inputs; keep as-is.

Implementation Notes (Where to Edit)

- File: app/templates/project.html
  - Section: connectMode IIFE (expose state to window and toggle it in setActive/cancel/keyup handlers).
  - Section: wireRevealSidebarOnNodeTap (add early return when connect mode active).
  - Section: any other auto-reveal logic (right-edge/hot zone) – add similar guard if applicable.

Rollout Plan

- Implement behind the simple runtime condition (no config toggle needed).
- Test locally across common flows.

Checklist (keep updated)

- [x] Expose connect-mode active flag on window
- [x] Guard reveal on node tap when sidebar hidden
- [x] Guard right-edge/hot-zone reveal (if present)
- [ ] Verify no reveal timers bypass guard
- [ ] Manual test T1–T7 pass
- [ ] Code review (self)

Changelog (fill during implementation)

- 2025-09-12: Drafted the plan and test cases.
- 2025-09-12: Implemented suppression: connect flag + node-tap guard + hot-zone guard.


