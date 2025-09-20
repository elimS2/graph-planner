Sidebar Hover Auto-Expand for Collapsible Sections — Roadmap

Status: Draft
Owner: UI/Frontend
Affected files: `app/templates/project.html`

1) Problem Statement

We want sidebar collapsible blocks (both Task panel and Settings panel) to temporarily expand on hover if they are currently collapsed, and auto-collapse when the cursor leaves to another block. Blocks that the user has manually expanded should not auto-collapse when the cursor leaves.

2) Initial Prompt (Translated to English)

We have expandable blocks in the sidebar — on the Task panel and on the Settings panel.

I want that if a block is collapsed, when the mouse hovers over it, it would expand, and when the mouse moves to the next block, it would automatically collapse. But this is only for blocks that are currently collapsed. If blocks are expanded, they should not be automatically collapsed when the mouse leaves.

Please analyze the task and the project deeply and decide how best to implement it.

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a `docs/features` folder for this. If there is no such folder, create it. Document in as much detail as possible all discovered and tried issues, nuances, and solutions, if any. As you progress on this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what decisions were made. Do not delete items for history; you can only update their status and comment. If, during implementation, it becomes clear that something needs to be added from the tasks — add it to this document. This will help us preserve context, remember what has already been done, and not forget what was planned. Remember that in the code and comments, labels of the project only the English language is allowed. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the UI.

3) Current Implementation Overview

- Sidebar is rendered in `app/templates/project.html` with tabs: Task, (optional) Actions, Settings.
- Each collapsible section has:
  - a toggle `button` with `aria-expanded` and a chevron element `[data-chevron]`.
  - a content body `div` that is shown/hidden by toggling Tailwind `hidden` class.
- Collapsible logic is centralized via `wireCollapsibleSection({ toggleId, bodyId, storageKey, defaultCollapsed })`:
  - Persists collapsed state in `localStorage` under `storageKey`.
  - Applies `hidden` class for collapsed, updates `aria-expanded`, rotates chevron.
  - Wires click and keyboard (Enter/Space) handlers to flip state.
- Sections are wired on tab activation in `showTask()` and `showSettings()`.

Implication: We already have a single place to augment behavior safely (inside `wireCollapsibleSection`) without scattering ad-hoc listeners.

4) Goals and Non-Goals

- Goals
  - Hover-peek: if a section is collapsed, hovering the block should temporarily expand it.
  - Auto-collapse on hover-out or when moving to another block, but only for sections that were collapsed before the hover.
  - Do not auto-collapse a section that is expanded (persisted open) by the user.
  - Provide a way to “pin” open while hover-peek is active (click to persist open, not close).
  - Keep interactions accessible and predictable; no flickering.

- Non-Goals
  - No change to persisted states beyond explicit user action (click/keyboard).
  - No changes to server or backend.

5) Design Principles

- KISS, DRY: Extend existing `wireCollapsibleSection` with opt-in hover behavior; avoid duplicate code.
- Separation of Concerns: Core apply/flip remains; hover-peek is an additive layer.
- Accessibility: Preserve keyboard interactions; hover is an enhancement only. ARIA remains accurate during hover-peek.
- Performance: O(1) listeners per section; minimal DOM thrash; no timers by default; optional small hover-intent delay if needed.

6) Proposed UX Behavior (Detailed)

- On pointer entering a section’s block area:
  - If the section’s body is currently collapsed (`hidden` present):
    - Expand it temporarily (remove `hidden`, set `aria-expanded="true"`, rotate chevron).
    - Mark it with `data-hover-open="1"` internally.
    - If another section is temporarily open due to hover, auto-collapse the previous one first.
  - If the section is already expanded (persisted): do nothing.

- On pointer leaving that block area:
  - If the section was opened by hover (`data-hover-open="1"`): collapse it back and clear the flag.
  - If it was expanded persistently: do nothing.

- On click while hover-peek is active:
  - Interpret as “pin open”: keep it open and persist state to expanded (localStorage = '0'), instead of toggling closed.
  - Clear `data-hover-open` to exit the transient mode.

- Keyboard behavior (Enter/Space on the toggle): remains unchanged; flips persistently as today.

7) Technical Design

- Augment `wireCollapsibleSection` to attach hover management in addition to existing click/keyboard logic.
- Data model and flags:
  - `body.dataset.hoverOpen = '1' | undefined` marks temporary expansion.
  - `toggle.dataset.storageKey = storageKey` helps during event handling.
  - Maintain a single global reference `window.currentHoverOpenBody` (or scoped in an IIFE) to auto-collapse a previously hover-open body before opening a new one.
- Container detection:
  - Use `const block = toggle.closest('div[id$="Block"]') || toggle.parentElement;` to attach `mouseenter`/`mouseleave` and to keep the whole block responsive (toggle + body area).
- Idempotency:
  - Reuse `toggle.dataset.wired` that already exists; extend with `toggle.dataset.hoverWired` to avoid double-binding hover events.
- Apply without persisting for hover-peek:
  - Reuse existing `apply(collapsed)` function; for hover, call `apply(false)` but skip writes to `localStorage`.
- Click “pin” semantics:
  - In `flip()` (click handler), if `body.dataset.hoverOpen === '1'`, then treat click as pin-open: call `apply(false)` and set `localStorage` to '0', then clear `hoverOpen` and return early (prevent normal flip).
- Auto-collapse previous hover-open:
  - On hover-enter, if `currentHoverOpenBody && currentHoverOpenBody !== body`, collapse it (if still hover-open) before opening the new one.

Pseudocode sketch:

```js
function wireCollapsibleSection({ toggleId, bodyId, storageKey, defaultCollapsed }) {
  // ...existing code...
  function apply(collapsed) { /* existing */ }
  function flip() {
    if (body.dataset.hoverOpen === '1') {
      // Pin open
      apply(false);
      try { localStorage.setItem(storageKey, '0'); } catch {}
      delete body.dataset.hoverOpen;
      return;
    }
    // ...existing flip logic...
  }
  if (!toggle.dataset.hoverWired) {
    const block = toggle.closest('div[id$="Block"]') || toggle.parentElement;
    const onEnter = () => {
      const isCollapsed = body.classList.contains('hidden');
      if (!isCollapsed) return; // respect persisted open
      if (window.currentHoverOpenBody && window.currentHoverOpenBody !== body) {
        if (window.currentHoverOpenBody.dataset.hoverOpen === '1') {
          // collapse previous hover-open
          window.currentHoverOpenApply(true, window.currentHoverOpenBody);
          delete window.currentHoverOpenBody.dataset.hoverOpen;
        }
      }
      apply(false);
      body.dataset.hoverOpen = '1';
      window.currentHoverOpenBody = body;
      window.currentHoverOpenApply = apply; // store reference to correct apply
    };
    const onLeave = () => {
      if (body.dataset.hoverOpen === '1') {
        apply(true);
        delete body.dataset.hoverOpen;
        if (window.currentHoverOpenBody === body) {
          window.currentHoverOpenBody = null;
          window.currentHoverOpenApply = null;
        }
      }
    };
    block.addEventListener('mouseenter', onEnter);
    block.addEventListener('mouseleave', onLeave);
    toggle.dataset.hoverWired = '1';
  }
}
```

Notes:
- We intentionally do not modify `localStorage` on hover-based open/close.
- We preserve ARIA and chevron state by using the unified `apply()` function.
- If needed, an optional small delay (e.g., 80–120ms) before opening on hover can be added to reduce accidental triggers; omitted initially for simplicity.

8) Implementation Plan (Tasks)

- [x] Extend `wireCollapsibleSection` to expose dataset markers (`data-hover-open`).
- [x] Add hover-peek wiring to `wireCollapsibleSection` with idempotency guard.
- [x] Adjust `flip()` to handle the “pin open” case when `data-hover-open` is set.
- [x] Ensure global tracking of the currently hover-open body to collapse previous one.
- [x] Add Settings toggle “Enable hover peek for collapsed sections” with persistence.
- [x] Guard hover-peek logic with the setting flag.
- [ ] Verify behavior on both tabs: `showTask()` and `showSettings()` wiring remains idempotent.
- [ ] Confirm ARIA updates remain correct in all transitions.
- [ ] Cross-browser check (Chromium, Firefox).
- [ ] Document code comments (English only) and update this roadmap.

9) Manual Testing Checklist

Task panel:
- Collapse a few sections manually; hover over each:
  - Expect temporary expansion on hover, auto-collapse on leaving to another collapsed section.
- Hover from one collapsed section directly to another:
  - Expect first auto-collapses when the second opens.
- Hover into an already expanded (persisted) section:
  - Expect no change; leaving should not auto-collapse it.
- While a section is hover-open, click its toggle:
  - Expect it stays open and remains open after moving the cursor away (pinned/persisted).
- Keyboard (Enter/Space) on toggle:
  - Expect normal persistent toggle; no interference from hover state.

Settings panel:
- Repeat the same scenarios; confirm parity with the Task panel.

Global behaviors:
- Switch tabs (Task/Settings) with some sections hover-open:
  - Expect no errors; hover-open resets naturally.
- Resize sidebar; no flicker or stuck states.

10) Edge Cases & Risks

- Rapid pointer transitions between blocks: managed by single active `hoverOpen` reference.
- Clicking during hover-open without moving:
  - Handled by pin-open logic; avoids double-click requirement.
- Nested interactive controls inside body:
  - Because listeners are on the block container, remaining inside the body maintains the open state; leaving the block collapses it only if it was hover-open.
- Persistence correctness:
  - Only explicit click/keyboard changes `localStorage`.

11) Rollback Plan

- The change is localized to `wireCollapsibleSection`. If issues arise:
  - Feature-flag hover-peek via a constant; or
  - Remove the hover wiring block (revert to current behavior).

12) Acceptance Criteria

- Collapsed sections expand on hover and auto-collapse upon pointer leaving or entering another collapsed section.
- Persistently expanded sections do not auto-collapse on pointer leave.
- Clicking a hover-open section pins it open persistently.
- No regressions in keyboard accessibility and ARIA state.

13) Open Questions

- Should we add a small hover delay (e.g., 100ms) to reduce accidental expansions?
- Should hover-peek be user-toggleable in Settings?

14) Changelog

- 2025-09-20: Draft created with analysis, design, and test plan.
- 2025-09-20: Implemented hover-peek with pin-open in `wireCollapsibleSection`; updated tasks.
- 2025-09-20: Added Settings toggle for hover-peek and wired it to logic.


