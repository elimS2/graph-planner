## Task Panel — Comment Editor Height Resizer

### Initial Prompt (translated to English)

We have a sidebar on the Task panel with a comments block and an input block for a new comment. Make it possible to adjust the height of the window where a comment is entered.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan of actions to implement this task in a separate document file. We have a `docs/features` folder for this. If there is no such folder, create it. Record in the document as thoroughly as possible all discovered and tried problems, nuances and solutions, if any. As you progress with this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what solutions were chosen. For history, do not delete items; you can only update their status and add comments. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code, comments, and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

### Context and Current State

- Sidebar and Task panel live in `app/templates/project.html`.
- Comments block uses:
  - `#taskCommentsBody` — resizable body with CSS var `--commentsHeight` applied (overall comments block height already resizable)
  - `#commentEditorArea` — Quill editor root for the new comment; currently `class="h-24"` (fixed height)
  - There is already a top and bottom resizer for the entire Comments block (`#taskCommentsResizerTop` and `#taskCommentsResizer`).
- Requirement for this task: make the comment editor input window itself user-resizable by height, independent from the whole comments block height.

### Goals

- Allow the user to adjust the height of the comment editor input area (`#commentEditorArea`).
- Persist preferred editor height across reloads (per device/browser).
- Ensure good UX and accessibility (mouse + keyboard, clear affordance, sensible min/max).
- Keep code and strings in English.

### Non-Goals

- Changing backend/API.
- Redesigning the editor or toolbar features.
- Affecting the existing overall Comments block height resizer (should continue to work).

### Design Options

1) Editor-only vertical resizer below the editor area
   - Add a separator element (e.g., `#commentEditorResizer`) immediately under `#commentEditor`.
   - Implement pointer-based drag to change a CSS variable `--commentEditorHeight`.
   - Apply min/max clamps, persist to localStorage.

2) Auto-size editor by content with max/min heights
   - Simpler, but removes user control; not persistent.

Chosen: Option 1 (explicit resizer with persistence).

### Technical Approach

- CSS: Define a new CSS variable `--commentEditorHeight` with default (e.g., `144px`, ~`h-36`), applied to the Quill container inner area (`#commentEditorArea`).
- HTML: Insert a horizontal resizer handle below the editor, visually similar to existing block resizers (thin bar, `cursor-row-resize`, `role="separator"`, `aria-orientation="horizontal"`, `tabindex="0"`).
- JS: Wire pointer events (`pointerdown/move/up/cancel`) to update the CSS variable. Persist `px` value under a distinct key, e.g., `sidebar.task.comments.editor.heightPx`.
- Clamps: `MIN_PX = 96` (6rem), `MAX_PX = 480` (30rem). Default around `192px` (12rem).
- Keyboard: ArrowUp/Down to nudge ±8px, PageUp/PageDown ±32px, Home resets to default, End to max.

### Data Persistence

- localStorage key: `sidebar.task.comments.editor.heightPx` (number in pixels).
- Load on page init; fallback to default if missing.
- Update on drag end and keyboard interactions.

### Edge Cases and Interactions

- When the overall Comments block height is small, the editor resizer must still respect `min` but not force overflow. The list above remains scrollable (`min-height: 0` on containers is already present).
- Collapsed Comments block: editor resizer is inert/hidden.
- Fullscreen Comments mode: editor height remains honored but still clamped within available space.

### Step-by-Step Plan (Implementation)

1) HTML edits in `app/templates/project.html`
   - Add `style` variable usage to `#commentEditorArea` to derive height from `--commentEditorHeight`.
   - Insert `div#commentEditorResizer` right under the editor container with appropriate classes/attrs.

2) CSS adjustments
   - Ensure `#taskCommentsContent` preserves `min-h-0` to let inner scrolls work.
   - Add inline style or small style rule to apply `height: var(--commentEditorHeight, 192px)` for `#commentEditorArea`.

3) JS wiring (in the same template where other UI JS lives)
   - Add `setupCommentEditorResizer()` to:
     - Read persisted value, apply to `--commentEditorHeight` on `#taskCommentsBody` or `#commentEditorArea` parent.
     - Handle pointer drag on `#commentEditorResizer` to update height in px with clamping.
     - Handle keyboard on the resizer for accessibility.
     - Persist on end.
   - Call `setupCommentEditorResizer()` along with existing sidebar/task initializers (after DOM is ready and Quill area exists).

4) Storage and lifecycle
   - If the Comments block is collapsed or hidden, skip interactions until expanded.
   - Re-apply persisted height on page reloads and when the Task tab becomes active.

5) Manual verification
   - Validate interplay with overall Comments block resizer, ensuring no layout thrash.

### Manual Test Plan (What to click)

1) Open a project and select a node to show Task panel.
2) Expand Comments block if collapsed.
3) Drag the new editor resizer to increase height; verify editor grows and comments list above still scrolls.
4) Drag to very small and very large sizes; verify clamping to min/max.
5) Release mouse; reload page; verify editor height persists.
6) Use ArrowUp/Down on the focused resizer to adjust height; verify small steps.
7) Use PageUp/PageDown for larger steps; Home to reset to default; End to set to max.
8) Toggle Comments Fullscreen mode (if used in your flow); verify editor height still reasonable.
9) Collapse/expand Comments block; verify no errors and height restored when expanded.

### Risks & Mitigations

- Conflicts with Tailwind fixed height classes (e.g., `h-24`)
  - Mitigation: Keep a default via CSS var and remove or override fixed classes where necessary.
- Event loss during drag
  - Mitigation: Use Pointer Events and `setPointerCapture`.
- Insufficient available space within Comments body
  - Mitigation: Inner containers keep `min-h-0`; list remains scrollable.

### Open Questions

- Should we also allow resizing the split between the comments list and the editor (two-way splitter)? For now, only the editor area height is resizable.

### Living Checklist (Update as work progresses)

- [ ] Add editor resizer handle and CSS var application in HTML.
- [ ] Implement pointer + keyboard JS for editor height.
- [ ] Persist and restore editor height.
- [ ] Manual test pass and refinements.
- [ ] Document outcomes and any nuances discovered.

### Notes on Principles

- SOLID/DRY/KISS: single responsibility for the new setup function; reuse existing patterns (resizers, storage keys); minimal and readable code.
- UI/UX: clear handle, consistent visuals, accessible keyboard controls, performance-conscious updates.

### Timestamp

- Created: 2025-09-10T19:58:28Z (UTC)


