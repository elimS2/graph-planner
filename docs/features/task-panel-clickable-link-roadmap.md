## Task Panel — Clickable Link in "Title & Link" Block

### Initial Prompt (translated to English)

We have a sidebar with a Task Panel tab. Inside it there is a block with a title and a link. I want the link there to be clickable.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step implementation plan for this task in a separate file-document. We have a folder `docs/features` for this. If there is no such folder, create it. Document in the file all identified and tried problems, nuances, and solutions, if any. As you progress with the implementation of this task, you will use this file as a todo checklist, updating it and documenting what was done, how it was done, what problems arose, and what decisions were made. For history, do not delete items; you can only update their status and comment. If, during implementation, it becomes clear that something needs to be added to the tasks — add it to this document. This will help us keep the context window, remember what we have already done, and not forget to do what was planned. Remember that only the English language is allowed in code and comments, labels of the project. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Include this prompt that I wrote in the plan, but translate it into English. You can name it something like "Initial Prompt" in the plan document. This is needed so that we can preserve in our roadmap file the exact context of the task statement without the "broken telephone" effect.

Also include steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.

Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.

Use Best Practices.

---

### Context and Current Behavior

- The sidebar UI is defined in `app/templates/project.html` inside the `<aside id="sidebar">`.
- The Task tab (`#taskPanel`) contains the combined block `#taskSelectionLinkBlock` (header text: "Title & Link"). Inside it there are:
  - `#selNodeTitle` — inline editable selected node title.
  - `#selNodeLinkUrl` — an `<input>` for the node's link URL.
  - `#openInNewTab` — a checkbox, persisted in `localStorage` and also PATCHed per-node as `link_open_in_new_tab`.
  - `#linkHint` — a small hint "Ctrl+Click node to open" that appears only if a link is present.
- Selecting a node populates these controls. Saving the link happens on blur/Enter via PATCH `/api/v1/nodes/:id` with `{ link_url }`.
- Currently, opening the link is primarily done by Ctrl+clicking the node in the graph. There is no clickable anchor in the sidebar block itself.

### Goal

- Make the link in the "Title & Link" block clickable directly from the sidebar.

### Non-Goals

- Do not change backend schema or API endpoints.
- Do not change how selection works or how the link is persisted.
- Do not modify link auto-open-on-oversized behavior; only augment the sidebar UI.

### UX Proposal

- Under the `Link URL` input, display a small, safe anchor that reflects the current value:
  - `id="selNodeLinkAnchor"` with discoverable label, shows either a truncated URL (host + path) or a static text like "Open Link" with an external-link icon.
  - Hidden/disabled when the URL is empty or invalid.
  - Honors the "Open in new tab" choice: target `_blank` or `_self`, plus `rel="noopener noreferrer nofollow"` for safety.
  - Nearby small `Copy` button to copy the URL to clipboard with success/failure feedback.
- Validation: only treat absolute `http:`/`https:` URLs as valid for the clickable anchor. Invalid/other schemes keep the input value but hide the anchor and show a subtle warning state.
- Accessibility: ensure link is reachable with keyboard, has `aria-label`, and focus ring; copy button has clear label and `aria-live` feedback.

### Implementation Plan

1) HTML updates (scoped to `app/templates/project.html`)
   - Inside `#taskSelectionLinkBody` after the input and hint row, add:
     - An anchor `<a id="selNodeLinkAnchor" class="text-xs text-blue-700 underline break-all hidden">Open Link</a>`.
     - A `Copy` button `<button id="copyNodeLink" class="text-xs px-2 py-0.5 rounded bg-slate-100 border">Copy</button>` placed inline with the anchor, both wrapped in a small flex row.

2) JS wiring (extend existing `wireLinkUrl()` and selection handler)
   - Extend the existing self-invoking `wireLinkUrl()` to:
     - Cache references to `selNodeLinkUrl`, `selNodeLinkAnchor`, `openInNewTab`, `copyNodeLink`, and `linkHint`.
     - Add a helper `parseValidHttpUrl(raw)`: returns a URL object or `null` if invalid/not http(s).
     - Add `applyLinkUi(raw)`: sets anchor `href`, text content (short form), `target` based on `openInNewTab` state, toggles visibility, updates hint visibility.
     - Call `applyLinkUi` on:
       - Input `input`/`change` events (debounced to keep UI responsive).
       - Checkbox `change` events.
       - After successful PATCH inside `commit()` to ensure normalized server value is applied.
   - In the `cy.on('tap','node', ...)` selection handler:
     - After populating `#selNodeLinkUrl` and hint, call `applyLinkUi(curLink)` so the anchor reflects the current node immediately.
   - Implement `Copy` button: uses Clipboard API (`navigator.clipboard.writeText`) with a brief, non-blocking toast/inline message; gracefully degrades if unavailable.

3) Security and Safety
   - For the anchor, always set `rel="noopener noreferrer nofollow"`.
   - Only enable the anchor for absolute `http`/`https` URLs. Hide/disable otherwise to avoid accidental execution of unsupported schemes.
   - Sanitize displayed text (never `innerHTML` for the link label).

4) Accessibility
   - Provide `aria-label` that includes the hostname (e.g., `"Open link to example.com"`).
   - Maintain visible focus styles, proper contrast, and keyboard operability.
   - For copy feedback, use an `aria-live="polite"` region or temporarily set `title`/tooltip text.

5) State Persistence
   - No new persistence is required. The anchor reflects the current input and server state.

6) Edge Cases
   - Empty value → anchor hidden, hint hidden.
   - Invalid URL (parse error or scheme mismatch) → anchor hidden, show subtle validation warning on the input.
   - Whitespace-only input → treat as empty.
   - Very long URLs → truncate text with CSS (`break-all`, `truncate` within a constrained container) and title attribute for full value.

### Manual Testing Checklist

- Select a node without a link:
  - The input is empty, hint is hidden, anchor is not visible.
- Enter a valid `https://` URL and blur the field:
  - PATCH succeeds; anchor becomes visible, text shows a sensible short form; clicking opens the link according to the checkbox.
- Toggle "Open in new tab":
  - The anchor updates its `target` immediately; clicking reflects the new behavior.
- Enter an invalid URL (e.g., `javascript:alert(1)` or `example`):
  - Anchor hides; input shows subtle invalid state; server PATCH should still be prevented or normalized by existing logic (we will not send non-http(s) values; see Implementation Notes below).
- Select a node with an existing link:
  - Anchor appears immediately and works; `Copy` button copies the exact URL; a success message appears.
- Keyboard navigation:
  - Tab to the anchor and press Enter; the link opens. Focus ring is visible and meets contrast.
- Empty the input and save:
  - Anchor hides; hint hides; node tap with Ctrl continues to show no auto-open.

### Implementation Notes

- Keep changes strictly inside `app/templates/project.html` (HTML + inline JS) to stay consistent with current architecture.
- Reuse existing storage keys and conventions; do not introduce new `localStorage` keys for this feature.
- Validation: In `commit()` before PATCH, if the input is a non-empty value that is not an absolute `http(s)` URL, either:
  - Option A (safer UX): do not send PATCH; show a small inline warning; keep anchor hidden.
  - Option B (minimal change): send as-is (current behavior), but the anchor remains hidden until it becomes a valid `http(s)` URL.
  - We will start with Option B to avoid changing server expectations and to keep the client lenient; anchor visibility remains the safety gate.

### Rollout & Risk

- Low risk: purely additive UI functionality; no server changes.
- Potential confusion if users enter non-`http(s)` values; mitigated by hint/warning and anchor visibility logic.

### Tasks (living checklist; keep history, update statuses inline)

- [ ] Add anchor + copy button markup in `#taskSelectionLinkBody`.
- [ ] Extend `wireLinkUrl()` with `applyLinkUi`, validation, and event wiring.
- [ ] Update node selection handler to call `applyLinkUi(curLink)`.
- [ ] Implement copy-to-clipboard with feedback.
- [ ] Add minimal invalid state UI for the input when URL is not valid `http(s)`.
- [ ] Manual test pass per checklist; fix issues found.
- [ ] Document decisions and any issues discovered during implementation.

### Changelog

- 2025-09-06: Drafted roadmap and implementation plan. Awaiting approval to implement.


