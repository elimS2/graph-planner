## Comments: Compact inline images with fullscreen viewer (messenger-like)

### Initial Prompt
The user asked to make pasted/sent images in comments display more compactly (like in messengers), and open them in fullscreen on click. Provide deep analysis of the task/project and decide the best implementation approach. Create a detailed roadmap in docs/features, including this prompt translated to English as "Initial Prompt". Keep the document as a living todo/checklist: track issues, nuances, and decisions without removing items (update status/comments instead). Include manual testing steps. Ensure code and UI texts are in English only. Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices, and UI/UX principles (User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design). Use Best Practices. If current time is needed, fetch from time MCP server.

### Context & Current Behavior
- Comments are created via a Quill editor in `app/templates/project.html` with paste/drag&drop upload handlers inserting `<img>` embeds for images (served via `/api/v1/files/<id>/<name>`).
- Comments render sanitized HTML (`x.body_html`) into `.comments-prose` containers in the sidebar list `#commentsList`.
- Problem: large images render at intrinsic size and can occupy excessive vertical space.

### Goals
- Show inline images in comments in a compact, bounded size by default (responsive, visually pleasant thumbnails).
- On click/tap, open image in fullscreen (modal/lightbox) with proper accessibility and keyboard/esc handling.
- Maintain good performance and not interfere with existing comment features (edit/delete, translations, attachments).

### High-Level Approach
1) Client-side CSS constraints within `#commentsList .comments-prose img` to cap max-height and add object-fit/rounded borders.
2) Client-side JS to wrap images with a clickable viewer trigger and implement a lightweight modal overlay using plain HTML/CSS/JS (no extra deps), supporting:
   - Open on click (and on Enter/Space when focused).
   - Close on overlay click, close button, or Escape.
   - Arrow keys for future multi-image nav (optional backlog).
3) Ensure uploaded links (`<a href="...">`) around images still behave; if we create our own wrapper, we should respect existing anchors by delegating.

### Detailed Plan (Step-by-Step)
1. Styling (compact inline)
   - Add CSS rules scoped to `#commentsList .comments-prose img`:
     - `max-width: 100%` (already typical), `height: auto`.
     - `max-height: 240px` (tunable), `object-fit: contain`, `border-radius: 6px`, subtle border/background.
     - Cursor: zoom-in to signal interactivity.

2. Viewer modal
   - Add a hidden overlay container to the page root (inside project.html), with image element and close button.
   - ARIA roles: `role="dialog"`, `aria-modal="true"`, focus trap minimal (send focus to close btn on open, restore on close).
   - Keyboard handling: Escape closes; Enter/Space on focused thumbnail opens.

3. Wiring thumbnails
   - After rendering each comment (`refreshLists`), find images inside the newly created `.comments-prose` and attach click handlers to open the viewer.
   - If an image is wrapped in an anchor `<a>`, still allow opening the viewer but prevent navigation when our viewer is active.
   - Store original `src` as high-res URL for viewer; consider using `srcset` later (backlog).

4. Editing mode
   - Ensure inline editor (Quill) does not inherit compact viewer styles; compacting applies only to display in the list, not in the editor.

5. Testing
   - Manual tests (see below) across paste, drag&drop, and attach flows.
   - Scripted smoke test (optional) can validate presence of modal elements in DOM after render.

6. Accessibility & UX
   - Provide `alt` propagation when possible (fallback to "image").
   - Maintain scroll position; viewer opening should not shift list unexpectedly.
   - Close button with visible label and screen-reader text.

### Manual Test Steps (UI)
1) Paste an image into the comment editor and submit.
   - Expected: In the comments list, the image shows as a compact thumbnail (max-height ~240px), with rounded corners and zoom cursor.
2) Click the thumbnail.
   - Expected: Fullscreen viewer opens, dark overlay, image centered and contained within viewport, Esc/close button closes viewer.
3) Keyboard tests
   - Tab to the image (it is focusable), press Enter/Space → viewer opens; press Esc → closes.
4) Anchor-wrapped images
   - If the image renders as a link, clicking still opens the viewer without navigating away; closing viewer returns focus.
5) Multiple images in one comment
   - Each opens the viewer independently; closing returns to same scroll position.
6) Mobile/small viewport
   - Thumbnails responsive; viewer scales to fit; scrolling disabled while viewer is open.

### Backlog / Optional Enhancements
- Swipe gestures on touch devices.
- Dedicated Download button and "Open original in new tab".
- Persist viewer zoom level / pan; add zoom/pan interactions.

### Implementation Checklist (ToDo)
- [x] Add compact image CSS under `#commentsList .comments-prose img`.
- [x] Add modal viewer (injected at runtime) to `project.html` with ARIA and Esc support.
- [x] Wire images inside rendered comments to open viewer; focusable; Enter/Space.
- [x] Add lazy-loading with skeleton; prefer server thumbnails via `?w&h`.
- [x] Add simple gallery navigation (ArrowLeft/ArrowRight).
- [x] Ensure overlay click/Close button close viewer and restore body scroll.
- [x] Keep editor unaffected; only the list view compacted.
- [x] Document decisions and results here.


