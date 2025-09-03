## Task Panel: Full WYSIWYG Editor for Comments

Status: Draft
Owner: System
Last Updated: 2025-09-03

### Initial Prompt (translated)

In the sidebar we have a Task Panel with comments. I need a full WYSIWYG editor there.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file, as detailed as possible, all the problems, nuances and solutions already discovered and tried, if there are any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve the context window, remember what has already been done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.


---

## 1) Current State Analysis

- Comments UI in Task Panel is a simple `<textarea>` and a flat list of text items.
  - Markup in `app/templates/project.html`:
    - Form: `#commentForm` with `<textarea name="body">` and submit to `POST /api/v1/nodes/{id}/comments`.
    - List container: `#commentsList`, items rendered as plain text with timestamp.
- Backend APIs (in `app/blueprints/graph/routes.py`):
  - `POST /api/v1/nodes/<node_id>/comments` uses `CommentSchema` and persists `body` as text only; forces authenticated user id.
  - `GET /api/v1/nodes/<node_id>/comments` returns comments and, when `?lang=xx` is provided, adds `body_translated` from `CommentTranslation`.
- Data model (in `app/models/__init__.py`):
  - `Comment.body` is `Text`, no HTML field.
  - `CommentTranslation.text` stores translated text, not HTML-aware.
- Translation service (`app/services/translation.py`):
  - Works on plain text; no HTML handling.

Implication: Introducing rich text requires safe HTML storage and rendering. Translations should either strip HTML or translate plain-text representation while preserving minimal formatting where feasible.


## 2) Goals and Non-Goals

- Goals:
  - Add a modern, accessible WYSIWYG editor in Task Panel for authoring comments.
  - Persist rich content safely; render sanitized HTML in the comments list.
  - Preserve existing translation workflow; optionally support translating plain text extracted from rich content.
  - Maintain graceful degradation when JS/CSS fail (fallback to textarea).
  - Keep UI responsive; no heavy bundles.
- Non-Goals (initial iteration):
  - Editing existing comments inline.
  - File/image uploads.
  - Complex collaborative editing.


## 3) Editor Choice and Strategy

- Candidate editors: Quill, TipTap, TinyMCE. Constraints: single-file template (`project.html`), no build step, small footprint.
- Decision: Quill 1.x via CDN (lightweight, API-stable, modular toolbar). Alternative: a plain contenteditable with minimal controls (fallback mode).
- Data strategy:
  - Store both `body` (plain text) and `body_html` (sanitized HTML) on server.
  - On create: client sends `{ body, body_html }`.
  - On list: server returns both when available; client renders `body_html` (trusted after sanitization), else `body_translated` or `body`.
  - Translation: operate on plain text (`body`), not HTML; do not attempt to translate `body_html` in v1.


## 4) Backend Changes

- DB migration:
  - Add nullable `comment.body_html: Text`.
  - No change to existing data; backfill optional.
- Schema:
  - `CommentSchema` accepts optional `body_html` (load/dump).
- API changes:
  - `POST /nodes/<id>/comments`: accept `body_html`; sanitize server-side; persist both `body` and `body_html`.
  - `GET /nodes/<id>/comments`: include `body_html` in payload (already sanitized).
- Security:
  - Add Bleach (python) to sanitize incoming HTML while allowing a safe subset: tags like `p, br, strong, em, u, s, code, pre, ul, ol, li, a, h1-h3, blockquote` and attributes `href`, `rel`, `target` with validation and `nofollow noopener noreferrer`.
  - Enforce max length in characters and an element count limit.


## 5) Frontend Changes (project.html)

- Add Quill CDN links (CSS/JS) with SRI, lazy-load only when Task tab is visible.
- Replace `<textarea>` in Task Panel with a container for Quill; keep a hidden `<textarea>` fallback.
- Toolbar: bold, italic, underline, strike, code, blockquote, lists, link, headers (H1–H3), clean.
- On submit:
  - Extract `quill.getContents()` plain text and `quill.root.innerHTML`.
  - Post `{ body: plainText.trim(), body_html: html }`.
  - Reset editor.
- Rendering:
  - If `x.body_html` present, inject into a container via `innerHTML` (safe since server sanitizes). Ensure link targets use `rel` guards.
  - Else fallback to `body_translated || body` text node.
- Accessibility:
  - ARIA labels for editor region, toolbar buttons have titles.
  - Keyboard shortcuts for basic formatting.
- Performance:
  - Lazy init Quill when first switching to Task tab.
  - Keep editor height reasonable; virtualize comment list later if needed.


## 6) Translation Pipeline Adjustments

- On batch translate endpoints, continue to translate `Comment.body` only.
- Do not attempt to translate `body_html` (v1). Optional: strip tags for safety if provider is sensitive.
- When listing comments with `?lang=xx`, continue to supply `body_translated`; UI prefers `body_html` if present (original language), then `body_translated`, then `body`.
  - Note: This means rich formatting is shown for original language only in v1. Future enhancement: HTML-aware translation or dual-rendering.


## 7) Manual Test Plan

1. Open a project, select a node to show Task Panel.
2. Type rich content: headings, bold, italic, list, link; click Add Comment.
3. Verify the new comment renders with formatting, links open safely in new tab.
4. Reload the page; verify the comment persists with formatting.
5. Switch language in Settings; verify translated comments still show as plain text if no `body_html`, and rich ones show original HTML while translation remains available in plain.
6. Paste HTML with scripts/iframes; ensure it is stripped.
7. Very long content; verify graceful truncation or scrolling in list.
8. Disable JS (or block Quill script); ensure the textarea fallback works and comment is saved as plain text.


## 8) Risks and Mitigations

- XSS risk: mitigate with strict server-side sanitization (Bleach), disallow style/event attributes, force `rel` on links.
- Bundle size: load Quill via CDN on demand; minimal modules.
- Translation fidelity: HTML not translated; user can rely on plain translation; document limitation.
- DB bloat: large HTML; enforce max size and prune unsupported tags.


## 9) Implementation Steps (Checklist)

- [ ] Create Alembic migration: add `comment.body_html` (Text, nullable).
- [ ] Add Bleach to `requirements.txt` and pin version; install.
- [ ] Update `CommentSchema` to include optional `body_html`.
- [ ] Update `POST /nodes/<id>/comments` to sanitize and persist `body_html`.
- [ ] Update `GET /nodes/<id>/comments` to return `body_html`.
- [ ] Integrate Quill in `project.html` with toolbar and lazy init.
- [ ] Submit both `body` and `body_html` from UI.
- [ ] Render comments preferring sanitized `body_html` else translated/body text.
- [ ] Adjust translation docs to clarify behavior.
- [ ] Add manual test script per workspace rules under `scripts/tests` to simulate payload and validate sanitization.


## 10) Open Questions

- Do we want to allow code blocks and syntax highlighting? (out of scope v1)
- Should we permit inline images/paste of images? (out of scope v1)
- Should translated view hide original HTML to avoid confusion? (current plan: show original HTML; translation displays as plain alternative when no HTML)


## 11) Change Log

- 2025-09-03: Draft created, current state analyzed, plan proposed.
- 2025-09-03: Added DB migration `comment.body_html`; added server-side sanitization with Bleach; updated `CommentSchema` and `POST /nodes/<id>/comments` to accept and sanitize `body_html`; UI integrated Quill editor in `project.html`; comments render sanitized HTML when present; translation pipeline remains on `body` only (no change required).

### Progress Checklist

- [x] Create Alembic migration: add `comment.body_html` (Text, nullable).
- [x] Add Bleach to `requirements.txt` and pin version; install.
- [x] Update `CommentSchema` to include optional `body_html`.
- [x] Update `POST /nodes/<id>/comments` to sanitize and persist `body_html`.
- [x] Update `GET /nodes/<id>/comments` to return `body_html`.
- [x] Integrate Quill in `project.html` with toolbar and lazy init.
- [x] Submit both `body` and `body_html` from UI.
- [x] Render comments preferring sanitized `body_html` else translated/body text.
- [x] Adjust translation docs to clarify behavior (translate `body` only).
- [x] Add manual test script per workspace rules under `scripts/tests` to simulate payload and validate sanitization.


