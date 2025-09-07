# Comment Attachments in Task Sidebar – Roadmap

Status: Draft (planning)
Owner: engineering
Created: 2025-09-07

## Initial Prompt (translated from Russian)

We have a comments block on the task panel in the sidebar. I want to allow inserting images or attaching files there. Inserting should work directly from the clipboard for both images and files.

Files should be stored in a folder specified in the .env file: a root folder for file storage. Inside it we should always save under the following structure: 2025/09/ — meaning we always take the current year and month and save the file there.

We need to create a separate table for files with id, created date, file type, name, storage path address, and other common fields as usually done in such cases. Then these ids should be linked wherever needed.

Analyze the task and the project deeply and decide how best to implement it.

Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a folder docs/features for this; if not present, create it. Document in the file any problems, nuances and solutions already discovered and tried, if any. As we progress in implementing this task, you will use this file as a todo checklist, updating it and documenting what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items; only update their status and comment. If during implementation it becomes clear that something needs to be added—add these tasks to the document. This will help us preserve context, remember what has already been done, and not forget to do what was planned. Remember that only English is allowed in the code and comments and project texts.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

---

## Current Project Analysis

- UI:
  - Sidebar comments live in `app/templates/project.html` with a Quill editor (`#commentEditorArea`).
  - Comments are rendered as sanitized HTML (`sanitize_comment_html`), currently allowing a limited tag set (no `img`).
  - POST new comments: `POST /api/v1/nodes/{node_id}/comments` via `graph` blueprint.
- Backend:
  - Models in `app/models/__init__.py`. `Comment` model exists; attachments model does not yet exist.
  - Schemas in `app/schemas/__init__.py` include `CommentSchema` but no attachments.
  - Routes for comments: `app/blueprints/graph/routes.py` (add, list, update, delete).
  - Sanitization forbids `img` and limits attributes/protocols; no upload endpoints.
- Config/env:
  - `.env` reader exists in `app/utils/env_reader.py` but no storage path config yet exposed in `config.py`.

## High-Level Design

- Storage root: read from `.env` as `FILES_ROOT` (absolute or path relative to project root). Fallback to `instance/uploads` if unset.
- Subdirectory structure: `YYYY/MM/` computed from UTC now at save time.
- File naming: content-hash-based filename with original extension to avoid duplicates and ensure stable URLs; additionally store original filename.
- Security:
  - Validate MIME type and extension; restrict to a safe allowlist (e.g., images: png, jpg, jpeg, gif, webp; docs: pdf, txt, md; optionally others).
  - Sanitize filenames; never trust client names for disk paths.
  - Generate signed or opaque IDs for download; avoid exposing raw filesystem layout in URLs.
  - Limit max size per file and per request; reject dangerous types.
  - Sanitize comment HTML: allow `img` tags but only pointing to our attachment URLs; strip other `img` sources.
- Database:
  - New table `attachment` with fields: `id`, `created_at`, `updated_at`, `uploader_user_id`, `mime_type`, `original_name`, `storage_path`, `size_bytes`, `width`, `height`, `checksum_sha256`, `kind` (image|file), `meta_json`.
  - Join table `comment_attachment` for many-to-many linkage (a file can be referenced by multiple comments; enforce via usage). Alternatively one-to-many if we want ownership; choose M2M for flexibility.
- API:
  - `POST /api/v1/attachments` (multipart/form-data) to upload. Returns attachment JSON and URL.
  - `POST /api/v1/attachments/clipboard` supporting pasted images via DataTransfer or Blob (still multipart under the hood).
  - `GET /api/v1/attachments/<id>` to fetch metadata.
  - `GET /files/<id>/<safe_name>` to serve file with proper headers; map id to disk; support `If-None-Match`/ETag and caching.
  - Extending comments:
    - Option A: Embed images in `body_html` pointing to `/files/<id>/<name>`; also send an `attachment_ids` array to associate and track references.
    - Option B: Separate attachments area under each comment. Start with Option A plus association to preserve references.
- Frontend:
  - Add toolbar actions: “Attach file”, “Paste image/file” with clipboard handlers on the editor container; support drag-and-drop.
  - On paste/drop/upload: call upload endpoint, receive attachment, insert at cursor as `<img>` for images or as `<a>` for generic files; also keep hidden `attachment_ids` in the form state.
  - Ensure sanitization allows our `img` and `a` links; prevent external `img` sources.
- Internationalization/translation: attachments are language-agnostic; translation flows unaffected.
- Backups: reuse existing backup service to include attachments metadata; optionally compress files directory.

## Data Model (Draft)

- Table `attachment`:
  - `id` (string UUID)
  - `uploader_user_id` (FK user.id, nullable=False)
  - `mime_type` (string, nullable=False)
  - `kind` (string: image|file, nullable=False)
  - `original_name` (string)
  - `storage_path` (string; relative path like `YYYY/MM/hash.ext`)
  - `size_bytes` (integer)
  - `width` (integer, nullable)
  - `height` (integer, nullable)
  - `checksum_sha256` (string, unique)
  - `meta_json` (text, nullable)
  - `created_at`, `updated_at`

- Table `comment_attachment`:
  - `comment_id` (FK comment.id, part of PK)
  - `attachment_id` (FK attachment.id, part of PK)

## API Changes (Draft)

- New endpoints (graph blueprint or dedicated `files` blueprint under `/api/v1`):
  - `POST /attachments` multipart form: fields `file` and optional `purpose`, returns `{ id, url, kind, mime_type, original_name }`.
  - `GET /attachments/<id>`: returns metadata.
  - `GET /files/<id>/<name>`: sendfile.
- Comments endpoints:
  - Accept optional `attachment_ids: string[]` on create/update; validate ownership; persist M2M.
  - On list, return `attachments` array per comment for rendering download thumbnails/links.

## UI/UX Changes (Draft)

- Editor (`#commentEditorArea`):
  - Add “Attach” button to toolbar (paperclip icon) opening file picker.
  - Paste and drag-and-drop handlers on editor root; detect `image/*` vs other types.
  - On successful upload:
    - For images: insert `<img src="/files/<id>/<safe-name>" alt="...">` at caret.
    - For other files: insert `<a href="/files/<id>/<safe-name>" target="_blank" rel="noopener">filename</a>`.
  - Maintain hidden field with `attachment_ids` for the submit payload.
- Rendering:
  - Enable `img` tag in sanitizer; restrict `src` to our domain path prefix `/files/`.
  - Style images to max-width: 100%, rounded corners, and captions via title.

## Validation and Security (Draft)

- Allowlisted MIME types and extensions; reject executable content.
- Max size per file (configurable, e.g., 25MB) and total per request.
- Virus scan hook placeholder (optional future work).
- Rate limiting on upload endpoints.
- Use content hash to deduplicate.
- Ensure auth: uploads require `login_required`.

## Step-by-Step Implementation Plan

1) Config and constants [Planned]
   - Add `FILES_ROOT`, `MAX_UPLOAD_MB`, `ALLOWED_MIME_LIST` to `BaseConfig` or a new settings helper.
   - Resolve root path (absolute) and ensure it exists; create subfolders lazily.

2) DB migrations [Planned]
   - Create models `Attachment` and association `CommentAttachment` in `app/models/__init__.py`.
   - Generate Alembic migration: create tables and indexes (checksum unique, FK constraints).

3) Schemas [Planned]
   - `AttachmentSchema` and `CommentWithAttachmentsSchema` or extend `CommentSchema` to include nested attachments on dump.

4) Services [Planned]
   - `services/uploads.py`: save file stream, compute hash, build path `YYYY/MM/`, persist metadata, return model.
   - Image probe: read dimensions for `image/*` when feasible.

5) API routes [Planned]
   - New blueprint `files` or extend `graph` with `/attachments` endpoints.
   - Upload (multipart), metadata, and file serving endpoints.
   - Extend comment create/update to accept `attachment_ids` and link via M2M.

6) Sanitization updates [Planned]
   - Allow `img` tag; allow `src` but only when it starts with `/files/`.
   - Keep `a` tags; ensure target rel attributes are safe on render side.

7) Frontend integration [Planned]
   - Add attach button and handlers to `project.html` Quill editor.
   - Implement paste and drop handlers; call upload; insert corresponding HTML; track `attachment_ids` in form.
   - Render attachments in comment list; ensure thumbnails display nicely.

8) Tests [Planned]
   - Backend: unit tests for upload service, API endpoints, sanitizer behavior, M2M linking.
   - Scripts: add `scripts/tests` Python for non-interactive checks per workspace rules; JSON output saved to `scripts/tests/json-result.json`.

9) Manual testing checklist [Planned]
   - See section below.

10) Docs and cleanup [Planned]
   - Update README or settings page to show storage root and quotas.
   - Add backup notes to include files or exclude by policy.

## Known Nuances and Decisions

- Quill sanitization: we must not allow arbitrary external images. Decision: allow only `/files/` paths in `img[src]`.
- Clipboard paste in browsers can include embedded images as `image/png` blobs; we handle via multipart upload on-the-fly.
- Deduplication vs retention: we will deduplicate by checksum but still allow multiple comments to reference the same attachment.
- Serving files via ID avoids path traversal and keeps URLs stable even if storage moves.

## Manual Testing Steps

1. Open a project, select a node so the task sidebar is visible.
2. In the Comments editor:
   - Click “Attach” and select a PNG image; verify it uploads and appears inline as an image.
   - Paste an image from the clipboard (Ctrl+V); verify upload and inline insertion.
   - Drag-and-drop a PDF file; verify a link is inserted with the filename.
   - Submit the comment; verify it renders with the image and link, persists after reload.
3. Edit the comment; add another attachment and save; verify both attachments render and metadata returns via API.
4. Delete the comment; verify the association row is deleted; the attachment remains if referenced elsewhere.
5. Open the file URL in a new tab; verify proper Content-Type and caching headers.
6. Try uploading a disallowed type (e.g., `.exe`); verify rejection with clear error.
7. Try large file beyond limit; verify 413-style error with message.
8. Verify sanitization blocks external `<img src="http://...">` when pasted; only our `/files/` loads.

## Open Questions

- Allowed MIME/extension set exact list and max size? (Default proposal: images up to 10MB, docs up to 25MB.)
- Keep attachments after all references removed, or GC unreferenced after N days? (Future work.)
- Thumbnails/previews for non-images? (Future work.)

## Progress Log

- 2025-09-07: Drafted analysis and plan. Pending approval to implement.
- 2025-09-07: Implemented backend foundations:
  - Config: `FILES_ROOT`, limits, and MIME allowlist.
  - Config loading now strictly from `.env` via `read_dotenv_values` (no `os.getenv`).
  - Models: `attachment` and `comment_attachment` (M2M) + migration.
  - Schemas: `AttachmentSchema`, `CommentWithAttachmentsSchema`.
  - Service: uploads with YYYY/MM path, SHA-256, dedup.
  - API: `POST /api/v1/attachments`, `GET /api/v1/attachments/<id>`, `GET /api/v1/files/<id>/<name>`.
  - Comments API now accepts `attachment_ids` and returns attachments.
  - Sanitizer: allow `img` with `src` restricted to `/api/v1/files/`.
  - UI: paste and drag-n-drop upload in Quill; auto-insert image/link; send `attachment_ids` on submit; added explicit "Attach" button with file picker.

- 2025-09-07: Iterations/fixes and enhancements:
  - Fixed duplicate upload constraint by checksum: reuse existing `Attachment` on re-upload (idempotent).
  - Allow submitting comments without plain text when there is HTML or attachments; backend ensures non-empty `body` fallback.
  - Fixed sanitizer compatibility with installed bleach version (custom img attribute filter).
  - Added ETag/Cache-Control for `GET /api/v1/files/...` with 304 handling.
  - Added soft rate limiting for `POST /attachments`.
  - Edit mode: attach files via button/paste/drag and persist `attachment_ids` on save.
  - Scripts: `attachments_login_upload.py`, `attachments_smoke.py`, `db_tables_check.py`, `server_restart.py`.

Next:
- Optional enhancements (nice-to-have):
  - Thumbnails/previews for non-image files.
  - Garbage collection of unreferenced attachments after a retention period.
  - Stronger rate limiting and quotas per user/project.
  - Include files directory in backup/restore flow (policy decision).
  - Fine-grained MIME/extension allowlist configuration via UI.


