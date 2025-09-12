# Sidebar Auto-Hide Lock When Node Selected – Roadmap

- Owner: core UI
- Created: 2025-09-12 (UTC)
- State: Draft (awaiting approval)

## Initial Prompt (English)

We have a sidebar that auto-hides. Please make it so that this sidebar does not auto-hide if we clicked on a point (i.e., a node is currently selected).

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in this file all discovered and tried issues, nuances, and solutions in as much detail as possible, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what was done, how it was done, what problems arose and what decisions were made. For history, do not delete items; you may only update their status and comment. If in the course of implementation it becomes clear that something needs to be added to the tasks—add it to this document. This will help us preserve the context window, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in code and comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## Context Overview

- Primary UI logic is in `app/templates/project.html`.
- Auto-hide engine and settings already exist: timers (`scheduleAutoHide`/`cancelAutoHide`), `sidebarHidden` flag, `applySidebarVisibility`, and edge reveal hot-zone.
- Node selection is handled by `cy.on('tap', 'node', ...)` where `selectedNodeId` is updated and side panel is refreshed.
- There is already wiring to reveal sidebar on node tap if hidden, and to schedule auto-hide after empty canvas clicks or pans.

## Problem Statement

- Current behavior: After interactions outside the sidebar, an auto-hide timer may hide the sidebar even when a node is selected on the graph.
- Desired behavior: When a node is selected (i.e., `selectedNodeId` is set and valid), the sidebar should not auto-hide. Auto-hide should be suspended until selection is cleared.

## Design Goals

- Prevent auto-hide while a node is selected.
- Maintain all existing behaviors (manual toggle, drag, 0px collapse, edge reveal, comments fullscreen) without regression.
- Keep the state model simple and predictable; avoid hidden coupling.

## Proposed Technical Approach

1) Selection-aware suspension flag
- Introduce a small helper `isSelectionLockActive()` that returns true when a node is currently selected.
- Integrate this check in the auto-hide engine: do not schedule or fire auto-hide if selection lock is active.

2) Event hooks
- On `cy.on('tap', 'node', ...)`: ensure auto-hide is cancelled and remains suspended while `selectedNodeId` is non-null.
- On background tap (`evt.target === cy`) and on edge selection (`cy.on('tap','edge', ...)`): clear node selection and allow auto-hide to resume.

3) Storage and settings
- No persistent storage required; selection lock is ephemeral runtime state.
- Respect existing `sidebar.autoHide.enabled` setting—if disabled, nothing changes.

4) API surface
- Reuse already-exposed `window.sidebarAutoHide` object to add an optional `isLocked` predicate if needed, but prefer local closure checks to avoid globals.

5) UX nuances
- If the sidebar is hidden and a node is selected, reveal should occur (already implemented). The lock only prevents subsequent auto-hide.
- If the user manually hides the sidebar (toggle click), honor the manual action even if a node is selected.
- If the user starts dragging the resizer or interacts with sidebar inputs, existing cancel/suspend rules remain.

## Implementation Steps (High-Level)

A. Identify core places:
- Auto-hide scheduler `scheduleAutoHide()` and guard checks.
- Node selection handlers and background tap clearing.

B. Add selection lock check:
- Define `function isSelectionLockActive(){ return !!selectedNodeId; }` near other auto-hide helpers.
- In `scheduleAutoHide()`: early-return if `isSelectionLockActive()`.
- In the mouseleave/focusout paths that call `scheduleAutoHide()`, no change is needed; the guard will prevent timer arming.

C. Cancel timer on selection:
- In `cy.on('tap','node', ...)` after setting `selectedNodeId`, call `cancelAutoHide()` if available.

D. Allow resumption on clear selection:
- In background tap handler and in edge tap handler (which nulls `selectedNodeId`), call `scheduleAutoHide()` to resume the natural behavior.

E. Manual hide precedence:
- Ensure toggle button path that sets `sidebarHidden='1'` continues to work regardless of lock (manual action wins). No code change expected.

F. QA and polish:
- Verify no unintended retention of lock state.

## Manual Test Plan

1) Basic lock
- Select a node. Move cursor away from sidebar and wait longer than auto-hide delay.
- Expected: sidebar remains visible and does not auto-hide.

2) Clear selection
- Click on empty canvas to clear selection.
- Expected: auto-hide resumes; after delay, sidebar hides.

3) Edge selection
- Select an edge (which clears `selectedNodeId`). Move cursor away.
- Expected: auto-hide works as usual after delay.

4) Manual hide override
- With a node selected, click the sidebar toggle to hide it.
- Expected: sidebar hides immediately; manual action overrides lock.

5) Hidden → select node
- Hide sidebar, then click a node.
- Expected: sidebar reveals (existing behavior). Keep it visible thereafter while the node remains selected.

6) Resizer and inputs
- With a node selected, interact inside the sidebar or drag resizer.
- Expected: no regressions; timer stays cancelled during interaction, and remains locked while selection is active.

## Risks & Mitigations

- Risk: Lock prevents auto-hide indefinitely if selection is never cleared.
  - Mitigation: This is intended; user can clear selection, manually hide, or navigate away. Optional future setting could cap lock duration.

## Tasks Checklist

- [ ] Add `isSelectionLockActive()` helper near auto-hide logic.
- [ ] Guard `scheduleAutoHide()` with selection lock.
- [ ] Cancel auto-hide on node selection; resume on selection clear.
- [ ] Verify manual toggle continues to override lock.
- [ ] QA per Manual Test Plan; document findings below.

## Change Log / Notes

- 2025-09-12: Drafted design to suspend auto-hide while a node is selected; scoped changes to `project.html` only to keep SoC and minimize risk.
