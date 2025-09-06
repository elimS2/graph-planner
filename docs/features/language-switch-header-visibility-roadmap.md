## Settings: Header Language Switcher Visibility — Roadmap

### Initial Prompt (translated to English)

We have a Settings tab in the sidebar; there is a block related to translation and switching the interface to the desired language. I want this language switcher to be controllable via a checkbox — whether to show it in the header or not. Similar to the buttons on the Actions tab.

=== Analyse the Task and project ===

Deeply analyze our task, our project and decide how best to implement it.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document all discovered and tried issues, nuances and solutions in as much detail as possible. As you progress in implementing this task, you will use this file as a todo checklist; you will update this file and document what has been done, how it was done, what problems arose and what decisions were made. Do not delete items for history, you can only update their status and comment. If during implementation it becomes clear that something needs to be added from tasks — add it to this document. This will help us preserve context, remember what has already been done and not forget to do what was planned. Remember that only the English language is allowed in code and comments, and in project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted.

Include steps for manual testing in the plan — i.e., what needs to be clicked in the UI.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow the UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.
Use Best Practices.

---

### Context and Current State (analysis)

- The project view template is `app/templates/project.html`.
  - The Settings sidebar contains a Translation block with a language selector `#settingsLangSelect` and translation actions.
  - The header toolbar previously had a language selector, but it is currently removed/commented conceptually: there is a line in script scope `const langSel = null; // toolbar lang removed; use Settings control`.
  - Language selection is persisted in `localStorage` under the key `displayLang`. Data reload flows through `handleLanguageChange(lang)`, which sets `displayLang`, ensures translations via `/translate`, fetches the graph, re-applies LOD and filters, and recomputes path colors.
  - The Actions tab implements a pattern for per-button header visibility controlled via `localStorage` keys like `actions.header.show.btnAddNode`. A small registry and a function apply header visibility toggling `hidden` class for header buttons.
- There is already a Settings checkbox pattern for other preferences (e.g., `#settingsShowHiddenToggle` mirrored with `localStorage` key `showHidden`).
- We need a checkbox in Settings (Translation block) that controls whether the language switcher is visible in the header. The behavior should be consistent with the Actions tab visibility toggles:
  - Persist a preference key in `localStorage` (proposed: `header.show.langSwitcher`).
  - On load, header applies the visibility based on this key.
  - Toggling the checkbox updates the key and immediately shows/hides the header switcher.
  - When both selectors exist (Settings and Header), they must be two-way synchronized to avoid divergent state.

Constraints and principles:
- Keep the implementation DRY: reuse existing helpers `handleLanguageChange(lang)` and `getCurrentLang()`; do not duplicate fetch logic.
- Maintain idempotent wiring: make event wiring guarded to avoid duplicate listeners.
- Accessibility: proper `aria-label`, focus styles, and keyboard navigation for the header selector and the Settings checkbox.
- Persistence: only `localStorage`—no back-end schema change is needed.

---

### Proposed Design

- Re-introduce a compact header language selector `#langSelect` (dropdown with options: `Original` -> value `""`, `English` -> value `"en"`). It will be controlled by a `localStorage` preference `header.show.langSwitcher` and will be hidden via `hidden` class when the preference is `0`.
- Add a checkbox in Settings → Translation block: `#settingsShowLangSwitcherInHeader` with label "Show language switcher in header". This checkbox is synchronized with the same `localStorage` key.
- Synchronization rules:
  - On page load: initialize both controls from `localStorage` (`displayLang` and `header.show.langSwitcher`).
  - On change in either language selector: call `handleLanguageChange(lang)` and update the other selector's value.
  - On checkbox toggle: update `header.show.langSwitcher` and immediately apply visibility to the header selector (toggle `hidden` class); persist across reloads.

Storage keys:
- `displayLang` — existing, selected language code or empty string for original.
- `header.show.langSwitcher` — new, `'1'` or `'0'`. Default: `'1'` (visible) to preserve previous behavior where the header switcher existed.

---

### Step-by-step Implementation Plan

1) Header UI
- Add a header language selector element `select#langSelect` in the toolbar (same place where it previously lived, near `#showHiddenToggle` and other controls). Use consistent styling (compact, label "Language").
- Wrap the selector in a container (e.g., `div#langSelectContainer`) to apply show/hide via class toggling for an entire compact block.
- Initialize its value from `localStorage.displayLang` on load.
- Wire `change` event to call `handleLanguageChange(lang)` and to synchronize the Settings selector if present.

2) Settings checkbox
- In the Translation block, add a new checkbox `#settingsShowLangSwitcherInHeader` with label "Show language switcher in header".
- On load, set its `checked` state from `localStorage.header.show.langSwitcher` (default true when key missing).
- On change, update the key and apply header visibility immediately.

3) Visibility application (utility)
- Implement a small utility `applyLangSwitcherHeaderVisibility()` that:
  - Reads `localStorage.header.show.langSwitcher` (default true).
  - Finds `#langSelectContainer` (or `#langSelect`) and toggles the `hidden` class accordingly.
- Call this utility on DOM ready, and after the Settings checkbox is toggled.

4) Two-way synchronization
- In `wireSettingsLanguage()`, after wiring `#settingsLangSelect`, also set up a mirror so that changes from header update Settings:
  - When header `#langSelect` changes, set `#settingsLangSelect.value = lang`.
  - When Settings selector changes, set `#langSelect.value = lang` if header control exists.
- Guard against redundant re-entrant updates (simple assignment is fine; `handleLanguageChange` already performs necessary effects).

5) Progressive enhancement and resilience
- If header selector is hidden or absent, Settings selector remains the source of truth and everything works as it does now.
- If the checkbox is unchecked, ensure `#langSelectContainer` is hidden but remains in the DOM to keep future toggles smooth.

6) Styling and A11y
- Add `aria-label="Language"` to the header selector and the Settings checkbox.
- Ensure focus outlines are visible and consistent with Tailwind classes used in the project.

7) Naming and keys
- Use the following identifiers:
  - Header selector: `#langSelect`
  - Header selector container: `#langSelectContainer`
  - Settings selector: `#settingsLangSelect` (already exists)
  - Settings checkbox: `#settingsShowLangSwitcherInHeader`
  - Visibility key: `header.show.langSwitcher`

8) Code placement (script scope inside `project.html`)
- Add `applyLangSwitcherHeaderVisibility`, `wireHeaderLanguage`, and `wireSettingsHeaderLangVisibilityCheckbox` in the same `<script>` scope where other wiring functions live (near other Settings wiring).
- Replace `const langSel = null;` with logic that obtains `document.getElementById('langSelect')` and wires it if present.

---

### Manual Test Plan

Prerequisites: Open a project page `/projects/{id}`.

1. Default visibility
- Ensure first load shows the header language selector (since default is visible).
- Confirm that the selector value matches Settings → Translation → Language (both in sync).

2. Toggle visibility off
- Open the Settings tab, Translation block.
- Uncheck "Show language switcher in header".
- Expected: the header language selector disappears immediately.
- Reload the page.
- Expected: the header selector remains hidden (preference persisted).

3. Toggle visibility on
- Check the checkbox back.
- Expected: header selector appears immediately.
- Reload the page.
- Expected: header selector still visible.

4. Change language via header
- With header selector visible, change language to `English`.
- Expected: graph reloads; LOD and filters re-applied; path colors recomputed. Settings selector updates to `English`.

5. Change language via Settings
- Change language in Settings to `Original`.
- Expected: same data refresh flow; header selector updates to `Original`.

6. Hidden header selector behavior
- Hide the header selector, then change language in Settings.
- Expected: everything works (no errors), and if the header selector is shown again later, its value matches the current language.

7. Persistence keys sanity
- Inspect `localStorage` to verify `displayLang` and `header.show.langSwitcher` values change as expected.

8. Accessibility
- Tab to the header selector when visible: ensure focus ring and keyboard navigation work.
- Tab to the Settings checkbox: ensure it is operable and announced by screen readers.

---

### Acceptance Criteria

- A checkbox in Settings → Translation controls visibility of the header language selector.
- Preference is persisted across reloads using `localStorage` (`header.show.langSwitcher`).
- When visible, the header selector is fully functional and synchronized with the Settings selector.
- Changing language via either control triggers the same data refresh flow (`handleLanguageChange`).
- No regressions to Actions tab visibility logic, translation jobs, or LOD/filtering.

---

### Implementation Checklist (living)

- [ ] Add header selector markup (`#langSelectContainer` + `#langSelect`) with correct styles and labels.
- [ ] Initialize and wire header selector (`wireHeaderLanguage`): set initial value, add change listener, sync to Settings.
- [ ] Add Settings checkbox (`#settingsShowLangSwitcherInHeader`) and wire it.
- [ ] Implement `applyLangSwitcherHeaderVisibility()` and call on load and on toggle.
- [ ] Replace `const langSel = null;` with DOM lookup and guarded wiring.
- [ ] Ensure two-way synchronization with `#settingsLangSelect`.
- [ ] Add small unit/integration smoke test (manual) per plan above.
- [ ] Code review for SOLID/DRY/KISS and a11y.

Status Legend: [ ] Planned, [x] Done, [~] In Progress, [!] Blocked

---

### Risks and Mitigations

- Duplicate event wiring: use dataset flags (e.g., `dataset.wired = '1'`) as already done elsewhere.
- Flicker on first render: apply visibility before layout (call visibility function as early as possible after DOM elements exist).
- Divergent state between selectors: always update the counterpart selector value after change events.
- Future expansion to more languages: keep options and wiring generic; the logic already uses `displayLang` string.

---

### Notes on Principles

- SOLID/DRY/KISS: reuse existing `handleLanguageChange` and `getCurrentLang`; centralize visibility toggle in one utility; keep event handlers small.
- Separation of Concerns: markup changes limited to header and Settings Translation block; logic isolated to wiring and tiny utilities.
- UI/UX: consistent labels, sizes, and focus styles; immediate feedback on toggle and language change; persistence of preferences.


