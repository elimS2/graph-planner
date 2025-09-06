## Task Panel — Comments Height Resizer

### Initial Prompt (translated to English)

We have a sidebar with a Task Panel tab. Inside it there is a Comments block where you can leave a comment or view existing ones. I want to be able to control this block by height. For example, if there are many comments, I should be able to set the height to 50% or even 75–80% of the screen height.

We already can adjust the sidebar width up to 100%; similarly, I want height adjustment here so that I can comfortably drag with the mouse to enlarge it.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how to best implement this.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan of actions to implement this task in a separate file-document. We have a folder `docs/features` for this. If there is no such folder, create it. Record in the document as thoroughly as possible all discovered and tried problems, nuances and solutions, if any. As you progress with this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what solutions were chosen. For history, do not delete items; only update status and add comments. If during implementation it becomes clear that something needs to be added from tasks – add it to this document. This will help preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt that I wrote in the plan, but translate it into English. You can name it something like "Initial Prompt" in the plan document. This is needed to preserve in our roadmap file the exact context of the task statement without the "broken telephone" effect.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

### Context and Current Behavior

- Sidebar UI lives in `app/templates/project.html`.
- Task Panel contains a Comments block with ids:
  - `#taskCommentsBlock` — container
  - `#taskCommentsToggle` — collapsible header
  - `#taskCommentsBody` — body container
  - `#commentsList` — list of comments; currently has `max-h-32 overflow-auto`
  - `#commentEditorArea` — Quill editor area; currently `h-24`
- Collapsible sections are wired via `wireCollapsibleSection(...)` with storage key `sidebar.task.comments.collapsed`.
- The sidebar already supports width resizing through a vertical resizer handle (`#resizer`), JS located near the bottom of the same template.

Implication: A similar horizontal resizer can be introduced inside the Comments block body to control height, persisted to localStorage.

### Goals

- Allow the user to resize the Comments block height using a mouse drag.
- Support practical ranges like 50% to 80% of viewport height, with sensible min/max clamps.
- Persist the chosen height across page reloads using localStorage.
- Maintain good UX: the resizer is easy to discover, draggable, and keyboard accessible.
- Keep code in English; follow SOLID, DRY, KISS; avoid unnecessary complexity.

### Non-Goals

- No backend/API changes.
- No redesign of comments content or editor; only layout/size behavior.
- No changes to other Task Panel blocks beyond necessary layout interactions.

### UX & Accessibility Guidelines

- Use a horizontal resizer bar visually distinct (e.g., a thin draggable area with cursor `row-resize`).
- Provide `role="separator"` and `aria-orientation="horizontal"` for accessibility.
- Keyboard adjustments: ArrowUp/ArrowDown/PageUp/PageDown to nudge height by small/large steps; Home/End to reset to min/max or default.
- Double-click on the resizer resets to default height (e.g., 32vh).
- Ensure the Comments list remains scrollable inside the resized area and the editor remains visible.

### Technical Design Options

1) Resize the entire Comments body using viewport-height units (preferred)
   - Convert `#taskCommentsBody` into a flexible column container.
   - Apply an inline style `height: <X>vh` based on saved value (default 32vh; clamp 20–80vh).
   - Inside, make `#commentsList` flex-grow with `overflow: auto`, and keep the editor area with fixed or min height.
   - Pros: Simple, viewport-relative, responsive on window resize.
   - Cons: Requires slight adjustment of existing Tailwind fixed heights (`max-h-32`, `h-24`).

2) Grid-based layout where the list takes `1fr` and editor is `auto`
   - Similar to option 1 but with CSS grid rows.
   - Pros: Explicit control; good for complex layouts.
   - Cons: Not necessary for current simplicity.

Chosen Approach: Option 1 — Flex column + `height: <vh>` on `#taskCommentsBody`.

### Deep Analysis and Best Practices (v2)

- Root cause of incorrect top-handle behavior:
  - We adjusted only inner scroll containers or temporarily used fixed overlays, so the visual drag didn't correlate with the actual block size in normal flow, causing a "snap back" after mouseup.
  - Height persisted as `vh`, but during drag we didn't update the same unit consistently on the same element.

- Best practices for resizable panels in constrained sidebars:
  - Resize the actual container in normal flow; avoid moving to `position: fixed` during drag (causes reflow jumps and misalignment against neighbors).
  - Use a single source of truth for size (CSS variable or inline style) and update it continuously during drag; persist on mouseup.
  - Compute height deltas relative to the handle origin:
    - Bottom handle: `newHeightPx = startHeightPx + deltaY`.
    - Top handle: `newHeightPx = startHeightPx - deltaY` so the bottom edge stays anchored.
  - Clamp with `clamp(min, val, max)` directly in CSS where possible to improve stability.
  - Use Pointer Events (`pointerdown/move/up/cancel`) with `setPointerCapture` to avoid lost events when the cursor leaves the handle.
  - Update `document.documentElement.style.setProperty('--var', value)` or element-level style for fewer layout thrashes; `requestAnimationFrame` throttle for large scenes.
  - Use `ResizeObserver` on the container to reconcile inner scroll areas and prevent overflow.
  - Keep accessibility: `role="separator"`, `aria-orientation="horizontal"`, keyboard arrows with predictable semantics (top handle ArrowUp increases size; bottom handle ArrowDown increases size).

- Recommended data model:
  - CSS variable on `#taskCommentsBody`: `--commentsHeight: 32vh`.
  - Style: `height: clamp(20vh, var(--commentsHeight), 80vh)` ensuring clamping at the CSS level.
  - Persist `--commentsHeight` in `localStorage` as a string value with a unit (e.g., `"48vh"`).

- Event model (pointer events):
  - On `pointerdown` on a handle, call `setPointerCapture`, store `startY`, `startHeightPx`, and which handle is active.
  - On `pointermove`, compute `proposedPx` with above formulas; update `--commentsHeight` to `${proposedPx}px` for smoothness.
  - On `pointerup/cancel`, convert to `vh` based on `window.innerHeight`, clamp, persist, and leave it in `vh` for responsiveness.

- Rendering model:
  - `#taskCommentsBody { display: flex; flex-direction: column; height: clamp(20vh, var(--commentsHeight, 32vh), 80vh); }`
  - `#commentsList { flex: 1 1 auto; min-height: 0; overflow: auto; }`
  - Editor area keeps a reasonable min-height.

### Revised Technical Design (v2)

1) CSS variable + clamp
   - Add inline style or a small `<style>` block to define height via CSS var and clamp.
   - On init, read saved value from `localStorage` (default `32vh`) and set `--commentsHeight` on `#taskCommentsBody`.

2) Pointer Events
   - Replace mouse listeners with `pointerdown/move/up/cancel` on both `#taskCommentsResizerTop` and `#taskCommentsResizer`.
   - Call `setPointerCapture` to keep events consistent.

3) Unified delta logic
   - Bottom handle: `startH + deltaY`.
   - Top handle: `startH - deltaY`.
   - During drag update CSS var in px; on finish convert to vh and persist.

4) rAF throttling (optional)
   - Wrap updates inside `requestAnimationFrame` to reduce layout thrash on low-end devices.

5) Accessibility
   - Keep current `role`, `aria-orientation`, `tabindex`.
   - Keyboard: top handle ArrowUp/PageUp increases height; bottom handle ArrowDown/PageDown increases height; Home/End to min/max; Enter to reset to default.

6) Observability
   - `ResizeObserver` on `#taskCommentsBody` (debug-only) to log and ensure inner scroll doesn't overflow; remove after validation.

### Migration Plan

- Replace current mouse-based logic with pointer-based unified function.
- Remove any remaining fixed/absolute overlay logic.
- Switch from inline style `height: 32vh` to CSS variable model with clamp.
- Keep storage key but value now includes unit (e.g., `"48vh"`).

### Expanded Manual Test Plan (v2)

1) Drag top handle up: top edge follows cursor; height increases; bottom stays fixed.
2) Drag top handle down: height decreases; no snap-back.
3) Drag bottom handle down/up: expected behavior.
4) Release mouse/finger outside the sidebar: capture keeps events; height persists.
5) Reload page: height restored from saved var.
6) Resize window: height remains within 20–80vh via clamp; visual size adapts to new viewport.
7) Keyboard on top handle: ArrowUp/PageUp increase height, ArrowDown/PageDown decrease; bottom handle inverse for arrows.
8) Dblclick on any handle resets to default `32vh`.
9) Screen reader sanity: separators are focusable and announced.
10) No overlapping/flicker of inner list/editor during drag.
11) Fullscreen: toggle on → only comments visible; height fills sidebar; width expands to max; toggle off → layout restored.

### Risks & Mitigations (v2)

- Pointer capture cross-browser quirks
  - Mitigation: fall back to mouse/touch listeners only if `setPointerCapture` is unavailable.
- CSS var not applied due to specificity
  - Mitigation: set directly on `#taskCommentsBody` element via `style.setProperty`.
- Unit mismatch (px vs vh) causing jumps
  - Mitigation: always convert and persist on `pointerup`; during drag use px only.

### Tasks Update

- [x] Analyze current comments block structure and wiring.
- [x] Implement v2: CSS var + clamp and pointer events.
- [x] Replace old mouse logic and overlays with unified handler.
- [x] Persist value with unit and migrate old numeric values.
- [x] Add top-handle UX scroll emulation (v2.1) to match visual expectation.
- [x] Add Comments Fullscreen mode (height + sidebar full width, toggle).
- [x] Thorough manual test per v2 plan.
- [x] Document outcomes and adjustments.

### Changelog

- 2025-09-06: Added deep analysis, best practices, and v2 design with pointer events and CSS variable model.
- 2025-09-06: Implemented v2; replaced old logic with CSS var + Pointer Events; persisted value with unit; added keyboard controls.
- 2025-09-06: Implemented v2.1 top-handle scroll emulation to keep bottom edge visually stable.
- 2025-09-06: Implemented Comments Fullscreen (expand height and sidebar width; hide other Task Panel blocks).

### Data Persistence

- localStorage key: `sidebar.task.comments.heightVh` (string integer, e.g., `50`).
- Apply on load; if missing or invalid, use default `32`.
- Clamp between `MIN_VH = 20` and `MAX_VH = 80`.

### Interaction Model

- Add a resizer element at the bottom of `#taskCommentsBody` (e.g., `div#taskCommentsResizer`).
- Drag logic:
  - On `mousedown` store start Y and start height (in px). While dragging, compute new height in px → convert to vh = `(px / window.innerHeight) * 100`.
  - Clamp to [MIN_VH, MAX_VH], set `style.height = vh + 'vh'` live for feedback.
  - On `mouseup`, persist to localStorage.
- Double-click resets to default.
- When collapsed, skip applying height and resizer visibility.

### Implementation Plan (Step-by-Step)

1) HTML structure updates in `project.html`
   - Wrap the body content of `#taskCommentsBody` into a flex column container that allows the list to grow.
   - Insert a horizontal resizer handle at the bottom: `#taskCommentsResizer`.
   - Remove fixed Tailwind height constraints from `#commentsList` and `#commentEditorArea` where they conflict; re-apply via styles where needed.

2) CSS/Tailwind adjustments
   - Add utility classes: `flex flex-col` for the body container; `flex-1 overflow-auto` for `#commentsList`.
   - Keep `#commentEditorArea` at a reasonable default height via a class (e.g., `min-h-24`) or inline style if necessary.

3) JavaScript wiring
   - Add functions to load, clamp, and apply the saved vh height.
   - Implement resizer drag listeners (document-level mousemove/mouseup) similar to the existing sidebar width resizer code.
   - Handle double-click reset and keyboard accessibility.
   - Persist to localStorage on end of drag.

4) Lifecycle integration
   - Apply height when initializing Task Panel wiring (same place as `wireCollapsibleSection` calls) and whenever the Task tab becomes active.
   - Hide or disable the resizer when the Comments block is collapsed.

5) Manual verification and fine-tuning
   - Ensure no layout overflow breaks the overall sidebar scroll.
   - Confirm persistence and clamping across reloads and window resizes.

### Manual Test Plan (What to click)

1) Open the project page; ensure the Task tab is active.
2) Expand the Comments block if collapsed.
3) Drag the new horizontal resizer to set height to around 50% of the screen; release mouse.
4) Reload the page; verify the height persists.
5) Drag to near 80% of the screen; verify it clamps at max.
6) Drag to below 20% of the screen; verify it clamps at min.
7) Double-click the resizer; verify it resets to default height.
8) While resized, scroll the comments list; ensure it scrolls independently and the editor remains visible.
9) Type in the editor; submit a comment; ensure behavior is unchanged.
10) Collapse and re-open the Comments block; ensure resizer and height restore correctly.
11) Switch between sidebar tabs and back; ensure height persists.
12) Test on different window sizes; ensure vh-based sizing scales appropriately.

### Edge Cases

- Collapsed state: height should not cause layout shifts; resizer hidden when collapsed.
- Very small viewport heights: clamp still yields usable editor space.
- Sidebar hidden: no errors; height reapplies when shown.
- Quill editor internal sizing: maintain a minimum editor area height to avoid unusable editor.

### Risks and Mitigations

- Risk: Conflicts with existing Tailwind fixed heights (`max-h-32`, `h-24`).
  - Mitigation: Replace with flex-based layout and explicit min-heights; test thoroughly.
- Risk: Drag math inaccurate on different zoom levels.
  - Mitigation: Use `vh` rather than raw px persistence; compute from `window.innerHeight`.
- Risk: Accessibility gaps for keyboard users.
  - Mitigation: Add `role`, `aria-*`, and keyboard handlers; document shortcuts.

### Open Questions

- Should the editor area height also be user-resizable (splitter between list and editor)? For v1, only outer Comments body is resizable; consider inner split in a follow-up.
- Maximum allowed height: 80vh vs 90vh? User requested up to 75–80%; default to 80vh max.

### Tasks (Living Checklist)

- [x] Analyze current comments block structure and wiring.
- [ ] Add resizable Comments body structure and resizer handle in `project.html`.
- [ ] Replace fixed heights with flex-based layout and min-heights.
- [ ] Implement JS for drag, clamp, persistence, keyboard, and reset.
- [ ] Integrate apply-on-load with Task Panel init and collapse handling.
- [ ] Manual test pass per checklist; fix issues found.
- [ ] Document decisions and any issues discovered during implementation.

### Changelog

- 2025-09-06: Drafted roadmap, design choices, and test plan.


