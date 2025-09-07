## Header Auto-Hide with Top-Edge Reveal – Roadmap

### Status
- Owner: core UI
- Created: 2025-09-07
- State: Implemented (pending QA)

### Initial Prompt (English)
Can we implement the same auto-hide behavior for the header? Create a separate roadmap.

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
- Header container is the top toolbar area in `app/templates/project.html` (between `<div class="flex items-center justify-between px-4 py-3">` and the main content).
- Sidebar already supports auto-hide with right-edge reveal; we should mirror a similar approach for the header with top-edge reveal.
- Header has interactive controls (search, filters, buttons) and an editable title `#projTitle`; focusing or editing the title must prevent auto-hide.

### Goals
- Auto-hide the header after an idle period when not hovered/focused.
- Reveal the header when the pointer approaches the top edge (configurable hot zone in pixels).
- Provide Settings UI to enable/disable and configure delay and edge threshold.
- Ensure interaction with the graph area and sidebar remains smooth; header reveal should not jitter the layout.

### Non-Goals
- Changing the header’s content or actions.
- Adding complex animations; a simple slide/opacity transition is sufficient.

### UX Design
- States: visible, auto-hidden.
- Auto-hide timer starts when the header loses focus and the pointer leaves the header area.
- Cancel auto-hide when hovering or focusing any header control (including `#projTitle`).
- Reveal on top-edge: moving pointer to the top hot zone shows the header.
- Optional: reveal on keypress of common shortcuts (e.g., `/` for search) if the header is auto-hidden.

### Technical Design
1) State & Storage
   - Keys:
     - `header.autoHide.enabled` ("1"/"0")
     - `header.autoHide.delayMs` (default 1500–3000 ms)
     - `header.autoHide.edgePx` (default 4–8 px)

2) Event Model
   - Observe `mouseenter`/`mouseleave` and `focusin`/`focusout` on the header container.
   - Observe `mousemove` on window; if `clientY <= edgePx` trigger a short debounce to reveal.
   - Suspend auto-hide during drag operations over the canvas if we decide header should remain visible; otherwise rely on idle timer.

3) Auto-Hide Engine
   - When eligible, set a timer. On fire: add a `header-hidden` class to the header container (or toggle `display` to none) and adjust layout so the graph expands.
   - Reveal path: remove `header-hidden` when hot zone is triggered or when a relevant key is pressed.

4) Settings UI
   - Add a new block in Sidebar → Settings → "Auto-Hide Header":
     - Enable [checkbox]
     - Idle delay [number ms]
     - Top edge hot zone [number px]
   - Persist to `localStorage` and apply changes live.

5) CSS
   - Add transition for header show/hide (e.g., `transform: translateY(-100%)` with `transition: transform 160ms ease`).
   - Ensure the main content shifts correctly without overlap.

6) Integration Points
   - Title editing (`#projTitle`) should cancel/suspend auto-hide while active.
   - If header is hidden and user hits `/` for search, reveal header and focus the search input.

### Edge Cases
- Sticky hover at the top edge should not cause flicker; use debounce.
- Window resize should not leave the header in a partially hidden state.
- Keyboard-only users: ensure that focusing the first header control reveals the header.

### Acceptance Criteria
- Header hides after the configured delay when not hovered or focused.
- Moving the pointer to the top edge reveals the header.
- Settings persist and apply immediately.
- Editing the title or interacting with header controls prevents auto-hide.
- No console errors; layout remains stable when header hides/reveals.

### Manual Test Plan
1. Enable auto-hide header; set delay to ~2 seconds; set top-edge hot zone to ~6 px.
2. Move pointer away; ensure header is neither hovered nor focused; wait for delay.
   - Expect: header slides up and hides; graph area expands accordingly.
3. Move pointer to the very top edge within the hot zone.
   - Expect: header slides down and becomes interactive.
4. Start editing the project title.
   - Expect: no auto-hide while editing; after blur + delay, it hides.
5. Press `/` (search) when header is hidden.
   - Expect: header reveals and the search input gets focus (if implemented).
6. Resize window and repeat; no flicker or stuck state.

### Tasks Checklist
- [x] Implement header auto-hide engine (timer, hover/focus detection, top-edge reveal with debounce).
- [x] Add Settings UI and persistence for enable/disable, delay, edge.
- [x] Add CSS transition and ensure layout reflows correctly (collapse height/padding; slide up/down).
- [x] Integrate with title editing and optional search key (focus cancels auto-hide; search key optional).
- [ ] QA: run Manual Test Plan and iterate.

### Engineering Notes / Observations Log
- 2025-09-07: Drafted plan mirroring the sidebar auto-hide architecture; identified header container in `project.html` as the target.


