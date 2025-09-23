# Task Panel — Selected Node Title: Plain-Text Paste Behavior

Status: Completed
Owner: Core UI
Updated: Completed today

## Initial Prompt (English)

The following is an English translation of the original task request to preserve full context without information loss:

"In our sidebar, in the task panel, there is a field

<div id=\"selNodeTitle\" contenteditable=\"true\" spellcheck=\"false\" class=\"text-sm text-slate-800 truncate border rounded px-2 py-1 focus:outline-none focus:ring focus:ring-slate-300\">Жакет Лакітка</div>

If you paste formatted text into it from some website, for example a bold title with a large font size, it gets pasted with that formatting. But for this field we must not preserve styles. It is just a title without styles. Unlike fields such as comments—there we must preserve formatting.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate document file. We have a folder docs/features for this. If there is no such folder, create it. Document in as much detail as possible all issues, nuances, and solutions already discovered and tried, if any. As you progress on the implementation of this task, you will use this file as a todo-checklist, updating it and documenting what was done, how it was done, what problems arose, and what decisions were made. For history, do not delete items, you can only update their status and comment. If, during implementation, it becomes clear that some tasks need to be added—add them to this document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and project comments and labels. When you write the plan, stop and ask me whether I agree to start implementing it or whether something needs to be corrected in it.

Include this prompt in the plan (translated into English). You can name it something like \"Initial Prompt\" in the plan document. This is needed to preserve the task setting context in our roadmap file as precisely as possible.

Also include steps for manual testing—what to click through in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

==================================================

=== Get time from MCP Server ===

If you need the current time, get it from the time MCP Server."

## Context and Current Behavior

- Selected Node Title field: `#selNodeTitle` is a `contenteditable` `<div>` in the Task Panel.
- Current wiring (in `app/templates/project.html`):
  - On node tap, it populates via `titleEl.textContent = evt.target.data('label') || '—'`.
  - Inline save on `blur` and on `Enter` (prevent default, blur) by `PATCH /api/v1/nodes/:id { title }`, then updates the Cytoscape label.
  - Previously there was no special paste handling, so browsers pasted rich HTML by default when available. Now handled by PlainPaste helper.
- Comments editor uses Quill with explicit rich paste and attachment handling. Comment formatting must be preserved and is unaffected by this change.

## Problem Statement

- Pasting from web pages or rich editors into `#selNodeTitle` brings over bold, size, links, spans, etc. The title must be plain-text only.
- We must keep rich formatting for comment fields.

## Goals

- Ensure that pasting into `#selNodeTitle` inserts plain text only (no HTML, no images, no links), normalizing newlines to spaces.
- Keep all existing title editing behaviors (focus/blur, Enter to commit, PATCH, Cytoscape data update).
- Do not impact comment editors or other fields that rely on rich paste.

## Non-Goals

- Do not introduce a full sanitization library here; we only need plain-text paste.
- Do not change server-side validation or add length limits at this stage.

## Design Overview

- Add a small, reusable wiring helper for plain-text paste:
  - Intercept `paste` on `#selNodeTitle`.
  - Read `text/plain` from `ClipboardEvent.clipboardData`.
  - `preventDefault()` and insert the plain text at caret position.
  - Replace `\r\n`/`\n` with single spaces and trim.
  - Ignore non-text clipboard payloads (files, images, HTML) for this field.
  - Optional guard: prevent `drop` (files/HTML) over the title field to reduce accidental rich content insertion.
- Keep implementation localized to the existing template script where `#selNodeTitle` is already wired (KISS, minimal surface area).

## Detailed Implementation Plan

1) Add utilities [DONE]
   - Implemented reusable helper in `app/static/js/plain_paste.js` exporting `window.PlainPaste`:
     - `sanitizePlainText(input, { allowNewlines })` — converts newlines to spaces (or `\n`), collapses whitespace, trims.
     - `insertTextAtCaret(containerEl, text)` — preserves caret, inserts as a text node.
     - `wirePlainTextPaste(el, { allowNewlines, preventDrop })` — intercepts `paste` and optionally guards `dragover/drop`.

2) Wire in `project.html` [DONE]
   - Included `<script src="/static/js/plain_paste.js"></script>` in `<head>`.
   - Replaced inline paste logic with `PlainPaste.wirePlainTextPaste(titleInlineEl, { allowNewlines: false, preventDrop: true })`.
   - Kept existing `keydown` (Enter) and `blur` handlers intact.

3) a11y enhancement [DONE]
   - Added `role="textbox"`, `aria-multiline="false"`, and `aria-label="Selected node title"` to `#selNodeTitle`.

4) Manual QA (see below) and code review

## Edge Cases & Notes

- Multi-line clipboard content: normalize to single line by replacing newlines with spaces.
- Very long paste: allowed; UI already truncates visually. No server limit changes now.
- Pasting links: treat as plain text; no anchor tags.
- IME/RTL: unaffected; paste path only.
- Browser support: `ClipboardEvent.clipboardData` supported in evergreen browsers; fallback to `window.clipboardData` (IE) not required.

## Risks and Mitigations

- Risk: Caret position loss if we use `textContent` replacement. Mitigation: insert at caret via `Range`/`Selection`.
- Risk: Unexpected DOM nodes from drag&drop. Mitigation: prevent `drop` on the title field.
- Risk: Over-sanitization removing necessary whitespace. Mitigation: conservative whitespace collapse only around newlines.

## Acceptance Criteria

- Pasting any formatted content into `#selNodeTitle` results in plain text only, without HTML tags or inline styles.
- Newlines from clipboard are replaced by single spaces.
- Comments editor behavior remains unchanged and still preserves formatting.
- Existing save-on-blur/Enter flows continue to work.

## Manual Test Plan

Preconditions: Open a project page with the sidebar Task Panel visible.

1. Paste rich title into Selected Node Title
   - Copy a bold, large headline from a website.
   - Click inside `Selected Node Title` (`#selNodeTitle`) and paste (Ctrl+V).
   - Expected: Only plain text appears (no bold, no size). Newlines are converted to spaces.

2. Paste multiline text
   - Copy a 2–3 line paragraph.
   - Paste into `#selNodeTitle`.
   - Expected: Single-line plain text; newlines replaced by spaces.

3. Paste into comments (regression)
   - Open the Comments editor (Quill).
   - Paste the same rich content.
   - Expected: Formatting is preserved as before; attachments paste/drag still work.

4. Drag and drop onto `#selNodeTitle`
   - Try dragging an image or formatted selection over `#selNodeTitle`.
   - Expected: Drop is blocked; no insertion occurs.

5. Save behavior
   - After paste, press Enter.
   - Expected: Prevent newline, commit occurs (PATCH), graph label updates.
   - Alternatively, blur by clicking elsewhere; same effect.

6. Keyboard and focus
   - Ensure caret remains correctly placed after paste.
   - Tab navigation and focus/blur work as before.

## Rollout Plan

- Single PR with focused change in `project.html` and this document.
- Manual QA per checklist across Chrome, Firefox, Edge (latest stable).
- If issues arise, behind-the-scenes feature toggle is unnecessary due to low risk; quick revert plan available.

## Implementation Checklist (living)

- [x] Analyze current code and identify wiring points
- [x] Implement `sanitize*` and `insertTextAtCaret` (via PlainPaste helper)
- [x] Implement `wirePlainTextPaste` and attach to `#selNodeTitle`
- [x] Add `role="textbox"`, `aria-multiline="false"`, `aria-label`
- [x] Manual QA smoke in primary browser
- [x] Update this document with results, decisions, and any fixes

## Testing Notes

- Smoke tested in primary browser: paste of bold/large header results in plain text only; multi-line paste coalesces to single line; drop is prevented; Enter/blur commit works; comments editor formatting remains intact.

## Decisions

- Do not implement length limit or visible counter at this time.
- e2e smoke automation not added in this iteration (manual QA sufficient for scope).

## Future Enhancements (optional)

- Centralize plain-paste helper to reuse for any other single-line contenteditable fields.
- Introduce a max length for titles with visual counter.

## References

- `app/templates/project.html` — inline wiring for `#selNodeTitle` (blur/Enter commit) and Quill comment editors.


