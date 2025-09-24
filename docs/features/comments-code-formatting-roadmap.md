# Task: Consistent Multiline Code Formatting in Comments

---

## Initial Prompt

User story (translated from the original request):

If I paste a multi-line text into a comment, for example:

```
#temp# 4 * * * * chmod -R 777 /var/www/invoice/src/Upload/ByBBL
#temp# 6 * * * * chmod -R 777 /var/www/invoice/src/Upload/Cabinet
#temp# 8 * * * * chmod -R 777 /var/www/invoice/src/Upload/Checks
```

and then select it and press the Code (</>) button to format it with a monospace font, it appears split into multiple blocks — one line per block — as shown in the screenshot. However, if I click Edit to edit this posted comment, select the same text and press the Code (</>) button again, the entire selected text becomes monospaced as one block, without being split across lines.

Analyze the task and project deeply and decide how best to implement this. Create a detailed step-by-step roadmap in `docs/features` documenting problems, nuances, and solutions. We'll keep this file updated as a to-do checklist, tracking what is done, how, and why. Include manual testing steps for the UI. Ask for confirmation before implementing.

Follow SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices, and UI/UX best practices (User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design).

---

## Context and Current Behavior

- Comments are authored and edited in the Task Panel within `app/templates/project.html` using Quill 1.x.
- Sanitization allows `pre` and `code` and is implemented by `sanitize_comment_html` (`app/utils/sanitize.py`).
- Rendering uses `innerHTML` into a container with class `comments-prose`.

Observed difference between create vs edit toolbars (source lines may drift, references indicative):

- Create toolbar includes inline code only:
  - Button: `ql-code` (inline code, wraps selection in `<code>` per line)
- Edit toolbar includes block code:
  - Toolbar options include `'code-block'` (wraps as `<pre><code>…</code></pre>`)

Implication: When a multi-line selection is formatted with inline code, Quill applies `code` format to each paragraph, giving a visual appearance of “separate code bits per line”. When formatted with `code-block`, Quill wraps the entire selection into one block, preserving line breaks as a single code block. This matches the user’s observation (split on create, unified on edit).

---

## Problem Statement

- Inconsistent UX: formatting multi-line selections as code produces per-line inline code during creation but a single block during editing.
- Users expect one consistent behavior: multi-line selection formatted as a single monospaced code block.

---

## Goals

- Make the Code button behavior consistent for new comments and edits.
- Default multi-line selections to a single code block (`<pre><code>…</code></pre>`), preserving line breaks.
- Keep inline code available as a separate, clearly labeled option (optional, if not confusing), or remove it to simplify.
- Preserve existing sanitization and security guarantees.
- Maintain accessibility and readable styling for code blocks and inline code.

---

## Non-Goals

- Syntax highlighting.
- Markdown support or conversion.
- Server-side transformation of HTML beyond the existing sanitizer.

---

## Root Cause Analysis

- Create toolbar uses `ql-code` (inline) but not `code-block`.
- Edit toolbar uses `code-block` (block) alongside other tools.
- Sanitizer and renderer already support `<pre>` and `<code>`, so the discrepancy is purely in toolbar configuration and the resulting Quill delta/HTML.

---

## Proposed Solution (High Level)

1) Unify toolbars to include `code-block` in both create and edit modes.
2) Option A (recommended): remove the inline `ql-code` button from create (and optionally from edit) to avoid confusion. Option B: keep both but rename tooltips to “Inline code” vs “Code block”.
3) Ensure CSS styles render code blocks as a single monospaced block with scroll for overflow, and inline code is visually distinct but subtle.
4) Keep sanitizer as-is (already allows `pre`, `code`).
5) Verify rendering pipeline and link safety remain intact.

---

## Detailed Implementation Plan

1) Frontend — New Comment Toolbar (file: `app/templates/project.html`)
   - Add `code-block` to the creation toolbar.
   - Decide on inline code presence:
     - Option A: remove `ql-code` to reduce ambiguity.
     - Option B: keep both `ql-code` and `code-block`; ensure distinct titles.
   - Ensure Quill initialization for creation mirrors the edit toolbar structure.

2) Frontend — Edit Comment Toolbar (file: `app/templates/project.html`)
   - Confirm `toolbarOpts` includes `code-block` (it already does).
   - Optionally harmonize button order and tooltips with the creation toolbar.

3) Styling (file: `app/templates/project.html` or a CSS module if we split later)
   - Ensure `.comments-prose pre` uses monospace font, appropriate padding, background, and horizontal scroll for long lines.
   - Ensure `.comments-prose code` (inline) is distinguishable with a subtle background and monospace.

4) Security & Sanitization (file: `app/utils/sanitize.py`)
   - No changes expected. Verify that `<pre>` and `<code>` remain in `ALLOWED_TAGS` and attributes are safe.

5) QA Manual Tests (see checklist below)

6) Documentation
   - Update this roadmap with outcomes and screenshots after verification.

---

## Acceptance Criteria

- Creating a comment: selecting multiple lines and clicking the Code button yields a single `<pre><code>` block preserving line breaks.
- Editing a comment: applying the Code button yields the same single block behavior.
- Inline code (if kept) is clearly labeled and applies only to the selection within a single line/phrase.
- Sanitization does not strip or fragment the block.
- Rendering shows a single visually cohesive block, without extra per-line wrappers.

---

## Manual Testing Checklist

1) Create Flow
   - Open a project → Task Panel → Comments.
   - Paste the sample multi-line cron lines.
   - Select all → click Code (block) button.
   - Submit. Verify rendered comment shows one code block with all three lines, monospaced.

2) Edit Flow
   - Click Edit on the comment.
   - Select all → click Code (block) button (or toggle off/on).
   - Save. Verify single code block remains.

3) Inline Code (if enabled)
   - Select a single word → click Inline code button.
   - Ensure only that word is wrapped in `<code>` and not converted to a block.

4) Mixed Content
   - Create a comment with text before/after the code block.
   - Ensure formatting does not merge adjacent paragraphs into the code block and spacing is correct.

5) Sanitization
   - Confirm images/links inside other comments still render and `rel/target` safety attributes are applied at render time.

6) Accessibility
   - Navigate with keyboard: ensure toolbar buttons are focusable and tooltips are meaningful.
   - High-contrast mode: code block remains readable.

---

## Edge Cases

- Pasting tabs or multiple spaces: code block should preserve whitespace visually; CSS must use `white-space: pre` for `<pre>`.
- Very long lines: horizontal scrolling instead of overflow clipping.
- Mobile: ensure code block wraps/scrolls appropriately without breaking layout.

---

## Risks & Mitigations

- User confusion between inline and block code: prefer a single Code action (block) or distinct labels.
- Styling regressions: test on light/dark themes if applicable and different browsers.

---

## Rollback Plan

- If issues arise, revert toolbar changes to previous configuration and keep edit-mode `code-block` only. No DB migrations involved.

---

## Work Items (to be checked off during implementation)

- [x] Add `code-block` to create toolbar; align with edit toolbar.
- [x] Decide on inline code presence (remove or relabel). Decision: remove inline `ql-code` in create toolbar; keep only `code-block`.
- [x] Add/update CSS for `.comments-prose pre` and `.comments-prose code`.
- [ ] Verify sanitizer behavior unchanged; keep allowed tags.
- [x] Execute manual test checklist; capture screenshots. Result: works as a single code block in create and edit.
- [ ] Update this document with results and any fixes.

---

## Notes / References

- Quill formats: inline `code` vs block `code-block`.
- Sanitization: `sanitize_comment_html` allows `pre` and `code`.


