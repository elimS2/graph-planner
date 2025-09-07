## Google OAuth 2.0 Sign-In Integration Roadmap

Status: Proposed
Owner: System
Last Updated: 2025-09-07

### Initial Prompt (translated)

Let's implement Google authorization — what is needed for this?

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how to best implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step plan of actions for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file, as detailed as possible, all the problems, nuances and solutions already discovered and tried, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. For history, do not delete items, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve the context window, remember what has already been done and not forget to do what was planned. Remember that only the English language is allowed in the code and comments, project labels. When you write the plan, stop and ask me whether I agree to start implementing it or if something needs to be adjusted in it.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

## 1) Problem Statement

We currently have username/password login via `/api/v1/auth/login` and session management via Flask-Login. There is no third-party OAuth. We want to add Google Sign-In so that users can authenticate with their Google account and be recognized as `User` records in our database with preserved roles.

## 2) Current Architecture Snapshot

- Flask app factory in `app/__init__.py` initializes `LoginManager` and registers blueprints.
- User model `app/models/__init__.py::User` has `id`, `email`, `name`, `role`, `password_hash` (nullable).
- API endpoints in `app/blueprints/users/routes.py` handle `/auth/login`, `/auth/logout`, `/auth/me` with server-side sessions.
- Frontend pages (`app/templates/index.html`, `app/templates/project.html`) call these endpoints using `fetch`.
- Config reads `.env` via `app/config.py`; no OAuth settings are present yet.

Implication: We can integrate Google OAuth 2.0 using the Authorization Code flow with server-side exchange, bind Google accounts to `User` by `email` (primary) and optionally store Google `sub` (subject) as a stable external ID. Because `password_hash` is nullable, passwordless Google-only users are supported.

## 3) Goals and Non-Goals

### Goals
- Add Google Sign-In (OAuth 2.0, Authorization Code with PKCE optional but recommended if we had public clients; since we are server-side, standard code flow is fine).
- Create `/api/v1/auth/google/login` (init) and `/api/v1/auth/google/callback` (redirect URI) endpoints.
- Verify ID token and fetch profile (email, name, picture). Trust only verified emails.
- Auto-provision user if not found by `email` (with default role `user`). Do not require password.
- Log in the user via Flask-Login session.
- Provide clear UX: a "Sign in with Google" button in header/login flow.
- Make configuration through environment variables.

### Non-Goals
- Multi-tenant / multiple identity providers beyond Google.
- Complex account linking UI. We will rely on email match; if `email` exists with different Google `sub`, we will log in the existing user and update the stored Google ID if needed (configurable).
- JWT stateless sessions; we keep server-side sessions.

## 4) Design Decisions

- Use `google-auth` and `requests` (already present) to verify ID tokens and fetch userinfo via Google OAuth endpoints.
- Store in config:
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
  - `GOOGLE_OAUTH_REDIRECT_URI` (e.g., `http://localhost:5000/api/v1/auth/google/callback` for dev)
  - `GOOGLE_OAUTH_SCOPES` default: `openid email profile`
  - Optional: `GOOGLE_OAUTH_HD` to restrict hosted domain
- Persist external identity fields:
  - Add nullable columns to `user`: `google_sub` (unique), `avatar_url` (optional) via migration.
- Security:
  - Use state parameter to prevent CSRF.
  - Validate token audience, issuer, expiry.
  - Require `email_verified = true`.

## 5) API Changes

- `POST /api/v1/auth/google/login` → returns a redirect URL or performs server redirect (since our UI is server-rendered, we can respond with 302 when called via `<a>`).
- `GET /api/v1/auth/google/callback` → handles `code` and `state`, exchanges code for tokens, verifies ID token, logs in user, then redirects to app (e.g., `/`).
- `GET /api/v1/auth/me` → unchanged; but should return user `email`, `name`, optional `avatar_url` for better UX.

## 6) Data Model Changes (Migration)

- Add to `user` table:
  - `google_sub` STRING unique nullable
  - `avatar_url` STRING nullable

Backfill: none needed; existing users remain with `password_hash` or can switch to Google later.

## 7) Configuration

Environment variables (read in `app/config.py`):
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_SCOPES` (default `openid email profile`)
- `GOOGLE_OAUTH_HD` (optional)

## 8) Implementation Plan (Checklist)

- [ ] Backend: Add config keys in `app/config.py`.
- [ ] Backend: Add migration to extend `user` with `google_sub`, `avatar_url`.
- [ ] Backend: Create `app/services/oauth_google.py` with helpers:
  - Build authorization URL (state, scope, prompt).
  - Exchange code for tokens.
  - Verify ID token (audience, issuer, expiry; email_verified).
  - Fetch profile (if needed) and normalize fields.
- [ ] Backend: Add routes in `app/blueprints/users/routes.py`:
  - `GET /api/v1/auth/google/login` → redirect to Google.
  - `GET /api/v1/auth/google/callback` → handle exchange, login, redirect.
  - Extend `/auth/me` to include `email`, `name`, `avatar_url`.
- [ ] Backend: Update `app/models/__init__.py::User` to include new fields and constraints.
- [ ] Frontend: Update `app/templates/index.html` and `app/templates/project.html` header auth UI:
  - Add a visible "Sign in with Google" button.
  - When logged in, show user name/email and avatar if present.
- [ ] Security: Implement `state` storage in session and validate upon callback.
- [ ] Error handling: Graceful messages on failure (invalid state, code exchange error, unverified email).
- [ ] Tests: Add basic integration tests in `scripts/tests/` as Python scripts producing JSON output per workspace rules.
- [ ] Docs: Update this roadmap with outcomes and decisions.

## 9) UX Notes

- Button label: "Sign in with Google" with clear affordance. Keep minimal, non-intrusive placement in header next to existing login button.
- After login, display short feedback (e.g., toast or header change). Avoid full page reloads when possible; redirects are acceptable on first login.
- Accessibility: Provide `aria-label` on the button; ensure keyboard focus order unaffected.

## 10) Risks and Mitigations

- Misconfigured redirect URI → Document exact URIs for dev/prod; assert in startup logs if missing.
- Email collisions (existing account with same email) → Log in as existing user; if `google_sub` differs, store or update depending on policy; never create duplicates.
- Unverified emails → Deny with clear message.
- Third-party outage → Keep local password auth as fallback.

## 11) Manual Test Plan

Preconditions:
- Valid Google OAuth credentials in `.env`.
- App running at the redirect URI host/port.

Scenarios:
1. Click "Sign in with Google" in header.
   - Expected: Redirects to Google consent screen.
2. Approve consent.
   - Expected: Returns to app; user is logged in; header shows user name/email and optional avatar.
3. Logout via existing "Logout" control.
   - Expected: Session cleared; Google button visible again.
4. Existing user with same email logs in via Google.
   - Expected: Existing account used; role preserved; no duplicate user created.
5. Unverified Google email (if you have such account or simulate)
   - Expected: Login denied with message.
6. Invalid `state` (manually tamper)
   - Expected: Denied with CSRF error.

## 12) Rollback Plan

Revert the new endpoints and migration; drop `google_sub` and `avatar_url` if needed. Local password auth remains unaffected.

## 13) Change Log

- 2025-09-07: Document created; analysis completed; proposed architecture and plan drafted.


