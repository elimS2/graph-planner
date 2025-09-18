# Allow ZIP, DOC, DOCX in Comment Attachments – Roadmap

Status: Draft (planning)
Owner: engineering
Created: 2025-09-18

## Initial Prompt (English Translation)

We can attach files in comments. Add the ability to attach zip, doc, and docx to the types that are already allowed.

Analyze the task and the project deeply and decide how best to implement it.

Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a folder docs/features for this; if it does not exist, create it. Document in the file all detected and tried problems, nuances, and solutions, if any. As you progress with this task implementation, you will use this file as a todo checklist, updating it and documenting what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items; only update their status and comment. If during implementation it becomes clear that something needs to be added—add these tasks to the document. This will help preserve context, remember what has already been done, and not forget to do what was planned. Remember that only English is allowed in the code and comments and project texts.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

Follow principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices. Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design. Use Best Practices.

---

## Current Implementation Overview

- Backend
  - Upload endpoint: `POST /api/v1/attachments` in `app/blueprints/graph/routes.py` calls `save_filestorage(...)` in `app/services/uploads.py`.
  - Allowlist is driven by `BaseConfig.ALLOWED_UPLOAD_MIME` (`app/config.py`). The service checks MIME via `_allowed_mime(...)`.
  - Attachments model and M2M exist in `app/models/__init__.py` (`Attachment`, `comment_attachment`).
  - File serving and sanitizer integration exist; client inserts `<img>` or `<a>` accordingly.
- Frontend
  - In `app/templates/project.html`: toolbar "Attach" button and hidden file input; paste and drag&drop upload; uses `/api/v1/attachments`.
  - No restrictive `accept` attribute for comment picker (it’s created dynamically during edit, and for new comments uses `#filePickerComment`).

## Goal

Allow attaching the following additional document/archive types in comments:

- ZIP: `application/zip`
- DOC (legacy MS Word): `application/msword`
- DOCX (OOXML): `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

Ensure end-to-end support: backend validation, optional frontend hints, tests, and documentation.

## Design Considerations

- Validation source of truth: server-side `ALLOWED_UPLOAD_MIME`.
- Frontend may optionally use `accept` hint on file inputs for better UX but must not rely on it for security.
- Security: no executable formats added; ZIP may contain arbitrary content but is served as opaque download; we do not auto-unzip or execute.
- Size limits: unchanged (`MAX_UPLOAD_MB`).

## Step-by-Step Plan

1) Configuration – extend allowlist [Planned]
   - Update `BaseConfig.ALLOWED_UPLOAD_MIME` default list to include the three MIME types above.
   - Document corresponding extensions in roadmap for clarity; server validates MIME from `FileStorage.mimetype`.

2) Service validation – no code changes expected [Planned]
   - `_allowed_mime` already checks against config; once config allowlist is extended, uploads will be accepted.

3) Frontend hints – optional [Planned]
   - For the new-comment hidden picker `#filePickerComment` and the edit-mode picker, optionally set `accept` to a conservative list covering images, pdf, txt, md, zip, doc, docx. This is a UX improvement only.

4) Tests [Planned]
   - Add scripts in `scripts/tests` to upload fixture files of types zip/doc/docx using the existing auth flow, verify 201 and response payload. Save JSON to `scripts/tests/json-result.json`.
   - Extend existing `attachments_smoke.py` if applicable, or add a new `attachments_accept_types.py`.

5) Docs [Planned]
   - Update `docs/features/attachments-roadmap.md` Known Nuances to reflect newly allowed MIME types.

## Manual Testing Checklist

1. Open a project and the comments editor in the sidebar.
2. Click "Attach" and pick files:
   - A `.zip` archive → expect link insertion and successful upload.
   - A `.doc` file → expect link insertion and successful upload.
   - A `.docx` file → expect link insertion and successful upload.
3. Submit the comment; reload the page and verify links still work and download with correct Content-Type.
4. Try uploading a disallowed type (e.g., `.exe`) to confirm it is rejected with a clear error.

## Risks / Notes

- Browser-detected `mimetype` for `.doc` and `.zip` is generally reliable but can vary; server trust is limited to Werkzeug’s detection; we rely on allowlist, not extension.
- Serving is download-only for these types; no inline rendering logic changes are needed.

## Progress Log

- 2025-09-18: Drafted plan to extend allowlist with zip/doc/docx. Pending approval to implement.


