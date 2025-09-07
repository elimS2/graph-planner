## Sidebar Auto-Hide with Edge Reveal – Roadmap

### Status
- Owner: core UI
- Created: 2025-09-07
- State: Implemented (pending QA)

### Initial Prompt (English)
I want the sidebar to automatically hide after some time if it does not have focus, similar to the Windows taskbar. When the mouse moves to the screen edge, the sidebar should slide out. This behavior should be toggleable in the sidebar Settings tab.

Create a separate roadmap file for this.

=== Analyse the Task and project ===

Deeply analyze our task, our project, and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document all discovered and tried issues, nuances and solutions in as much detail as possible, if any. As you progress with the task, you will use this file as a to-do checklist, keep updating this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items; you may only update their status and add comments. If during implementation it becomes clear that something needs to be added to the tasks – add it to this document. This will help us preserve the context window, remember what we have already done and not forget to do what was planned. Remember that only the English language is allowed in code, comments, and project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this exact prompt translated to English into the plan (you can name it something like "Initial Prompt"). This is needed to preserve the context of the task in our roadmap file as accurately as possible without the "broken telephone" effect.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.


### Context and Constraints
- Primary UI is in `app/templates/project.html`. Sidebar width and visibility are already managed with drag, toggle logic, persistence (`localStorage`), and a resizer sync.
- We added 0 px min-width support, `collapsed` visual polish, and nuanced Toggle behavior. The auto-hide feature must coexist with these behaviors.
- We need a Settings toggle (enable/disable), configurable delay (e.g., 1–10 seconds), and possibly hot zone width for the screen-edge reveal.

### Goals
- Auto-hide sidebar after an idle period when it does not have focus/hover.
- Reveal sidebar when the pointer hits the configured screen-edge hot zone.
- Make the feature optional and configurable in the sidebar Settings tab.
- Respect existing drag/toggle logic and persistence without surprises.

### Non-Goals
- Changing the sidebar layout or resizer structure.
- Introducing complex animations framework; a simple CSS transition is enough.

### UX Design
- States: visible, hidden, collapsed-to-0 (width = 0), and auto-hidden (hidden due to idle).
- Auto-hide timer starts when:
  - Sidebar loses focus and pointer leaves the sidebar/resizer area, and no drag is active.
  - Optional: pause auto-hide if a context menu or dropdown inside sidebar is open.
- Cancel auto-hide when:
  - Pointer re-enters sidebar/resizer, or sidebar gains focus, or any interaction inside sidebar occurs.
  - User begins drag on resizer/Toggle.
- Reveal on edge: moving pointer to a right-edge hot zone (e.g., 2–8 px) shows the sidebar (restores width per stored width or default).
- Visuals: optional subtle slide-in/out with CSS transition on `width` and/or `transform`.

### Technical Design
1) State and Storage
   - Keys:
     - `sidebar.autoHide.enabled` ("1"/"0")
     - `sidebar.autoHide.delayMs` (default 2000–4000 ms)
     - `sidebar.autoHide.edgePx` (default 4–8 px)
     - Reuse `sidebarWidth` and `sidebarHidden` for width/visibility; introduce `sidebar.prevWidthAutoHidden` for restoring after auto-hide.

2) Event Model
   - Observe: `focusin`, `focusout`, `mouseenter`, `mouseleave` on `#sidebar` and `#resizer`.
   - Observe pointer at window level to detect hot zone: `mousemove` => if `(viewportWidth - clientX) <= edgePx` start a short reveal debounce.
   - Integrate with existing drag logic: while dragging, suspend auto-hide.

3) Auto-Hide Engine
   - On eligible loss of focus/hover, start/restart a timer (`setTimeout` with `delayMs`).
   - If timer fires and feature enabled: set `sidebarHidden = '1'` (or collapse to 0?), store `prevWidthAutoHidden`, and call `applySidebarVisibility()`.
   - Reveal path: when hot zone is triggered, set `sidebarHidden = '0'`; restore width from `prevWidthAutoHidden` (fallback to default width) and call `applySidebarVisibility()`.
   - Guardrails: do not auto-hide if sidebar is already hidden or width is 0 due to explicit user action (optional policy toggled by setting "Respect 0 width as pinned").

4) Settings UI (Sidebar → Settings tab)
   - Add a new block "Auto-Hide Sidebar" with controls:
     - Enable auto-hide [checkbox]
     - Idle delay [number ms or select: 1s, 2s, 3s, 5s, 10s]
     - Edge hot zone width [number px]
     - Option: Treat width=0 as pinned (disable auto-hide until expanded)
   - Persist to `localStorage` and apply changes live.

5) CSS
   - Add transitions (e.g., `transition: width 180ms ease, transform 180ms ease`) for smooth slide.
   - Ensure `collapsed` class remains compatible; when hidden via auto-hide, `display` should be none to prevent tab stop unless we prefer a transformed off-screen state.

6) Integration with Existing Toggle/Drag
   - Toggle click logic remains intact. When auto-hidden, click/edge reveal should restore to the previous width (or default) and cancel any pending timers.
   - Dragging cancels auto-hide timer until mouseup.

### Edge Cases
- Ongoing text editing inside sidebar (contenteditable/inputs) should suspend auto-hide.
- Modals or popovers anchored in the sidebar should suspend auto-hide until closed.
- Rapid mouse movements flickering near the edge → debounce edge reveal.
- Extremely small screens: re-clamp width after reveal; never overflow.

### Acceptance Criteria
- Auto-hide hides the sidebar after the configured idle delay when not hovered/focused.
- Edge reveal shows the sidebar on pointer near the right edge within the configured hot zone.
- Settings can enable/disable and configure idle delay and edge zone at runtime; settings persist across sessions.
- Auto-hide coexists with manual 0-width and manual hide/show; no unexpected fights between engines.
- Resizer visibility and graph layout update correctly on hide/reveal; no console errors.
- Hover over sidebar/resizer prevents auto-hide; click/drag on the graph (empty space/pan) restarts the auto-hide countdown.
- Clicking a node when hidden reveals the sidebar and restores a sensible width.

### Manual Test Plan
1. Enable auto-hide in Settings; set delay to 2–3 seconds.
2. Blur the sidebar: move pointer away and focus elsewhere; wait.
   - Expect: sidebar hides after delay; resizer also hidden.
3. Move pointer to right screen edge (within hot zone).
   - Expect: sidebar reveals; restores previous width (or default); resizer visible.
4. Start dragging the resizer and keep pointer within sidebar.
   - Expect: auto-hide timer does not fire during drag; resumes after mouseup and idle.
5. Set width to 0 manually; enable "Treat width=0 as pinned" (if implemented).
   - Expect: auto-hide does not auto-hide further; edge reveal still works.
6. Hide via Toggle, then move to edge.
   - Expect: edge reveal shows sidebar; settings persist across reloads.
7. Click a node while the sidebar is hidden.
   - Expect: sidebar reveals; width restored to default if previously < threshold.
8. Click empty canvas or pan the graph after reveal.
   - Expect: auto-hide countdown starts; sidebar hides after the configured delay if pointer is away.
9. Resize window; set a very large width and repeat steps.
   - Expect: dynamic clamping works; no overflow.

### Tasks Checklist
- [x] Implement auto-hide core engine (timers, focus/hover detection, reveal hot zone at right edge).
- [x] Add Settings UI and persistence for enable/disable, delay, edge width (and optional pinned policy).
- [x] Integrate with toggle/drag logic; suspend timers while dragging.
- [x] Start auto-hide countdown on empty canvas click and on pan.
- [x] Reveal sidebar on node click when hidden.
- [x] Add brief inline help texts for settings.
- [ ] QA per Manual Test Plan; document findings and tweaks below.

### Additional Enhancements Implemented
- Right-edge hot zone reveal with small debounce.
- Inline help texts for all Auto-Hide options.
- Reveal on node tap when hidden; restore to default width if below threshold.
- Auto-hide schedule triggered by empty canvas click and pan events.

### Engineering Notes / Observations Log
- 2025-09-07: Drafted plan; identified low-risk integration points in `project.html` and Settings panel wiring.


