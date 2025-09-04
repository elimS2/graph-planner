## Task Panel Comments: Rich Text Rendering (Lists, Headings, etc.)

Status: Proposed
Owner: System
Last Updated: 2025-09-04

### Initial Prompt (translated)

In the sidebar we have a task panel with comments.

There is a visual editor. When saving a comment, not everything is displayed correctly in the saved comment, for example, bulleted or numbered lists are not displayed.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file, as detailed as possible, all the problems, nuances and solutions already discovered and tried, if there are any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve the context window, remember what has already been done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## 1) Current State Analysis

Observed issue: comments saved from the WYSIWYG editor render without list formatting (bulleted/numbered lists) in the task panel.

Findings from code review:
- Frontend (`app/templates/project.html`):
  - Quill is loaded via CDN and initialized for the comment editor. On submit, both plain text (`quill.getText().trim()`) and HTML (`quill.root.innerHTML`) are sent to the API as `{ body, body_html }`.
  - When rendering comments, if `x.body_html` is present, it is inserted via `innerHTML`; otherwise falls back to plain text (or translations).
- Backend (`app/blueprints/graph/routes.py`):
  - `POST /api/v1/nodes/<node_id>/comments` accepts `body_html`, sanitizes it with `sanitize_comment_html`, and stores alongside `body`.
  - `GET /api/v1/nodes/<node_id>/comments` returns `body_html` when present.
- Sanitization (`app/utils/sanitize.py`):
  - Allowed tags include `ul`, `ol`, `li`, plus headings, inline formatting, code, blockquote, and `a` links.
  - Bleach configuration uses `strip=True` and allows `http/https/mailto` protocols.
- Data model (`app/models/__init__.py`): `Comment.body_html` exists and is nullable.
- Requirements include `bleach==6.2.0`.

Conclusion: The pipeline already supports HTML lists end-to-end. If lists do not render, likely causes include:
1. Quill editor not producing list HTML in some flows (e.g., toolbar not active, HTML empty, or `body_html` set to null when text is empty).
2. CSS resets in the comments list container collapsing list styles (e.g., `list-style: none` on `ul, ol` or `display: inline` injection).
3. Sanitizer stripping required structural tags (unlikely since `ul/ol/li` are allowed, but confirm no extra wrappers are removed).
4. Rendering markup inside an inline element (e.g., wrapping in `<span>` may affect layout/margins, but should not hide bullets unless `list-style` is suppressed).

## 2) Goals and Non-Goals

Goals:
- Ensure saved comments with lists, headings, and basic formatting render correctly and accessibly in the task panel.
- Maintain server-side sanitization for XSS safety.
- Preserve existing translation behavior (translate `body` only).

Non-Goals (this fix):
- Rich editing of existing comments.
- Image/file uploads or advanced embeds.

## 3) Root Cause Hypotheses and Checks

H1: CSS reset removes bullets or margins.
- Check `#commentsList` and global styles. If Tailwind base resets affect `ul, ol`, add scoped styles within comments container to restore `list-style`, `padding-left`, and margins.

H2: Sanitization drops list-related classes/attributes required by Quill.
- Quill lists typically render as semantic `ul/ol/li` without special attributes. Verify HTML samples survive sanitize step.

H3: Frontend wraps HTML inside an inline element.
- Replace wrapper with a `div` and apply a prose-like class to render block content properly.

H4: HTML saved as empty due to empty `getText()` guard.
- Ensure `html` is only nulled for truly empty text. Confirm Quill’s `<p><br></p>` case is the only scenario nulled.

## 4) Proposed Changes

Frontend (scoped rendering styles and structure):
- Render `body_html` into a block element (`div`) with a comments-prose class instead of a `span`.
- Add minimal scoped CSS rules in `project.html` to ensure lists display correctly within the task panel comments area:
  - `.comments-prose ul { list-style: disc; padding-left: 1.25rem; margin: 0.25rem 0 0.5rem; }`
  - `.comments-prose ol { list-style: decimal; padding-left: 1.25rem; margin: 0.25rem 0 0.5rem; }`
  - `.comments-prose li { margin: 0.125rem 0; }`
  - Reset margins for headings/paragraphs to look good in the sidebar.

Backend:
- No change expected to sanitization rules for lists (already allowed). Document the allowlist explicitly in this roadmap and keep Bleach pinned.

Docs:
- Document behavior and limitations: we display sanitized HTML; translations remain plain text.

## 5) Manual Test Plan

Preconditions:
- Open a project and select a node to reveal the task panel.

Tests:
1. Create a bulleted list via toolbar and save. Expect bullets to show with proper indentation.
2. Create a numbered list and nested list (indent/outdent). Expect numbering and nesting to render.
3. Mix list items with bold/italic and links. Links open in new tab with `rel` guards.
4. Add a blockquote and a code block; verify formatting persists (monospaced for code, quote styling minimal but readable).
5. Reload the page; formatting remains.
6. Switch UI language; for comments with `body_html`, original formatted content shows; for plain comments, translation appears as plain text.
7. Paste unsafe HTML (script/iframe). Expect it to be stripped.
8. Very long list: container scrolls without breaking layout.

## 6) Rollout and Risks

Risks:
- Overly aggressive CSS could affect other parts of the page.
- Future Tailwind updates could change base resets; keep styles scoped via a unique class on comment root.

Mitigations:
- Scope all CSS under `#commentsList .comments-prose`.
- Keep sanitizer strict; do not allow style attributes or event handlers.

## 7) Implementation Steps (Checklist)

- [ ] Update `project.html` comment rendering: use `<div class="comments-prose">` instead of `<span>` for `body_html`.
- [ ] Add scoped CSS in `project.html` to restore list bullets and indentation in `.comments-prose`.
- [ ] Verify sanitizer keep `ul/ol/li` intact; adjust if necessary (documentation only, no code changes expected).
- [ ] Manual testing per plan; capture screenshots if possible.
- [ ] Update this roadmap with results and mark items done.

## 8) Change Log

- 2025-09-04: Document created; analysis completed; proposed scoped CSS and rendering container change.


