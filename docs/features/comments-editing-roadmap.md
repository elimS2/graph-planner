## Task Panel — Comments Editing (Inline Edit/Delete, WYSIWYG-safe)

### Initial Prompt (translated to English)

We have a sidebar with a Task Panel; inside it there is a Comments section. I want to be able to edit these comments.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, comprehensive step-by-step plan of actions to implement this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Record in the document as thoroughly as possible all discovered and tried problems, nuances and solutions, if any. As you progress with this task, you will use this file as a todo checklist, updating this file and documenting what was done, how it was done, what problems arose and what solutions were chosen. For history, do not delete items; only update status and add comments. If during implementation it becomes clear that something needs to be added from tasks – add it to this document. This will help preserve context, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in the code and comments and project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include in the plan steps for manual testing, i.e., what to click in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## 1) Current State Analysis

- Backend
  - Model `Comment` already exists with fields: `id`, `node_id`, `user_id`, `body`, `body_html`, timestamps.
  - Endpoints:
    - `POST /api/v1/nodes/<node_id>/comments` — creates a comment; forces `user_id` via `_fallback_user_id()`; sanitizes `body_html` with `sanitize_comment_html`.
    - `GET  /api/v1/nodes/<node_id>/comments` — lists comments; supports `?lang=` to attach `body_translated` from `CommentTranslation`.
  - There are NO endpoints yet for updating or deleting individual comments.
  - Sanitization pipeline exists in `app/utils/sanitize.py` with Bleach and Quill list-indent preprocessing.

- Frontend (template `app/templates/project.html`)
  - Comments UI is in Task Panel → `#taskCommentsBlock`.
  - List container: `#commentsList`; items render either `body_html` (sanitized on server) via `innerHTML` or plain `body` text.
  - New comment form uses Quill editor (`#commentEditorArea`) and posts JSON with `{ body, body_html }` to `POST /nodes/{id}/comments`.
  - Utilities exist: `postJSON`, `patchJSON`, `del` wrappers, and auth helpers.
  - Height resizing and fullscreen for comments are already implemented and persisted in `localStorage`.

Implication: We can add inline editing with Quill to reuse existing toolbar/sanitization. We must implement backend PATCH/DELETE for comments, ensure permissions, and update the UI to allow edit/cancel/save, plus delete with confirmation.

## 2) Goals and Non-Goals

- Goals
  - Enable editing existing comments inline in the Task Panel.
  - Allow deleting a comment with confirmation and optimistic UI update.
  - Preserve WYSIWYG content: edit in Quill with the same sanitization pipeline.
  - Respect permissions: only the author (or admin) can edit/delete.
  - Keep translation behavior: display `body_translated` when listing with `?lang=xx`; editing affects the source `body/body_html` only.
  - Maintain accessibility and consistent UI/UX with the current design.

- Non-Goals (initial iteration)
  - Versioning/history of comment edits.
  - Inline translation editing.
  - Attachments/images.

## 3) API Design

- Add endpoints in `app/blueprints/graph/routes.py`:
  - `PATCH /api/v1/comments/<id>`
    - Auth required.
    - Body: partial `{ body?: string, body_html?: string }`.
    - Sanitize `body_html` with `sanitize_comment_html` before saving.
    - Authorization: only comment author or admin.
    - Response: `{ data: CommentSchema }`.
  - `DELETE /api/v1/comments/<id>`
    - Auth required; authorization as above.
    - Response: 204.

- Validation
  - Use `CommentSchema(partial=True)` for PATCH.
  - Ensure at least one of `body` or `body_html` is non-empty after trimming; reject empty updates with 400.

## 4) Authorization Strategy

- Reuse `_fallback_user_id()` only for creation; for edit/delete, require active `current_user`.
- Implement helper `can_manage_comment(user, comment)` to allow:
  - user.id == comment.user_id OR user.is_admin (if such a flag exists; if not, gate by ownership only).
- Return 403 on unauthorized operations.

## 5) Frontend UX Design (Inline Editing)

- For each comment item in `#commentsList`:
  - Render metadata: author (if available later), timestamp.
  - Actions: `Edit`, `Delete` buttons for comments owned by current user; hide or disable otherwise.
  - On `Edit`:
    - Replace the static body with an inline editor area (a lightweight Quill instance or a shared single-instance editor rebound to the item).
    - Controls: `Save`, `Cancel`.
    - Save → call `PATCH /api/v1/comments/{id}` with both `body` (plain text extracted) and `body_html` (editor HTML delta converted to HTML), then refresh the item in-place.
    - Cancel → restore the original view.
  - On `Delete`:
    - Confirm dialog; if confirmed → `DELETE /api/v1/comments/{id}`, remove item from DOM.

- Consider a single floating editor instance to keep bundle small; mount/unmount into item container to avoid multiple Quill instances.

## 6) Data Handling

- Listing remains via `GET /nodes/{nodeId}/comments`.
- For ownership checks client-side, fetch current user once via `/api/v1/auth/me` when Task Panel opens; compare to `user_id` from comment payload.
- If `body_html` present → render via `innerHTML` into a `comments-prose` container; ensure outbound links open safely.

## 7) Edge Cases

- Editing to empty content: block on client and server.
- Network failures: show error banner; do not lose original content on cancel.
- Concurrent updates: optimistic update but fallback to re-fetch the list if PATCH returns stale/update conflict (future improvement: ETag/versioning).

## 8) Step-by-Step Implementation Plan (Checklist)

- [ ] Backend: Add `PATCH /comments/<id>`
  - [ ] Load comment by id; 404 if missing.
  - [ ] AuthN required; AuthZ via ownership (and admin if available).
  - [ ] Validate input; sanitize `body_html`.
  - [ ] Save and return updated comment.

- [ ] Backend: Add `DELETE /comments/<id>`
  - [ ] Load comment; check permissions; delete; 204.

- [ ] Frontend: Render actions for own comments
  - [ ] Fetch current user with `/api/v1/auth/me`; store `currentUserId`.
  - [ ] In list renderer, for each comment where `x.user_id === currentUserId`, append `Edit` and `Delete` buttons.

- [ ] Frontend: Inline editing flow
  - [ ] Create a shared Quill instance for editing existing comments (separate from the new-comment editor) with the same toolbar options.
  - [ ] On `Edit`, mount editor into the comment item, prefill with existing HTML/plain text.
  - [ ] Implement `Save` → collect text and HTML, call `PATCH`, update DOM.
  - [ ] Implement `Cancel` → restore DOM without changes.

- [ ] Frontend: Delete flow
  - [ ] Confirm dialog; `DELETE` on confirm; remove item.

- [ ] Translations
  - [ ] When `?lang=xx` is active, still allow editing the source; indicate visually that translation view is shown and editing updates the original.

- [ ] Accessibility & UX
  - [ ] Keyboard: focus management when entering/exiting edit mode.
  - [ ] Buttons have labels and focus rings; ARIA where needed.
  - [ ] Preserve existing resize/fullscreen behavior.

- [ ] Tests (manual + lightweight script hooks where appropriate)
  - [ ] Manual test plan (see below).
  - [ ] Optional: add minimal API tests for PATCH/DELETE.

## 9) Risks & Mitigations

- Missing admin concept → only owners can edit/delete.
- Multiple Quill instances → performance. Mitigation: single shared instance.
- Sanitization stripping necessary markup → expand `ALLOWED_TAGS/ATTRS` if justified.
- Auth flows vary (fallback user exists). Editing should require login; otherwise hide actions.

## 10) Manual Testing Steps

1. Open a project page and select a node with comments (or create a new comment).
2. Ensure you are logged in; verify `Edit` and `Delete` are visible only for your own comments.
3. Click `Edit` on your comment: an editor appears inline with the same toolbar.
4. Modify content (e.g., add a list, bold text). Click `Save`.
5. Verify the comment updates in place with sanitized HTML preserved.
6. Reload page; the change persists and looks identical.
7. Attempt to edit a comment that is not yours → actions are hidden; try calling API manually and expect 403.
8. Click `Delete` on your comment; confirm; verify it disappears; reload page; it is gone.
9. Switch UI language and load comments; ensure `body_translated` continues to display, but editing still changes the source.
10. Resize comments block and toggle fullscreen to ensure the editor works well within varied heights.

## 11) Implementation Notes

- Keep server responses consistent with existing schema `CommentSchema`.
- Keep client code localized to `project.html` for now to avoid scope creep.
- Reuse existing `patchJSON` and `del` helpers.
- Ensure link handling in rendered HTML sets `rel="noopener"` and safe target behavior.

## 12) Progress Log

- 2025-09-06: Wrote analysis and roadmap; awaiting approval to implement.


