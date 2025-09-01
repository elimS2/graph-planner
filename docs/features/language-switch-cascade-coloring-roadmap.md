### Language Switch breaks cascade coloring (Roadmap)

---

### Initial Prompt

If you switch languages, cascade coloring of the graphs does not work. Only the graph that leads to the priority point is colored.

=== Analyse the Task and project ===

Deeply analyze our task and our project and decide how best to implement this.

==================================================

=== Create Roadmap ===

Create a detailed, step-by-step action plan for implementing this task in a separate file-document. We have a folder docs/features for this. If there is no such folder, create it. Document in this file in as much detail as possible all the problems, nuances, and solutions that have already been discovered and tried, if any. As you progress with the implementation of this task, you will use this file as a to-do checklist, you will update this file and document what has been done, how it was done, what problems arose, and what solutions were made. For history, do not delete items; you can only update their status and comment. If, during implementation, it becomes clear that something needs to be added from the tasks — add it to this document. This will help us keep the context window, remember what has already been done, and not forget to do what was planned. Remember that only the English language is allowed in code and comments, project labels. When you write the plan, stop and ask me if I agree to start implementing it or if something needs to be adjusted in it.

Also include in the plan steps for manual testing, i.e., what needs to be clicked in the interface.

==================================================

=== SOLID, DRY, KISS, UI/UX, etc ===

Follow the principles: SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
Follow UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design
Use Best Practices

---

### Context and Current Behavior (analysis)

- The project uses Cytoscape in `app/templates/project.html` to render nodes/edges and color paths based on priority.
- Cascade path coloring is computed in `recomputePriorityPaths()` via reverse BFS from not-done high/critical nodes and sets `edge.data('pathPriority')` to `high`/`critical` upstream.
- Edge styles include both cascade-based coloring and direct target-based coloring:
  - `edge[pathPriority = "high"|"critical"]` (cascade)
  - `edge[targetPriority = "high"|"critical"][targetStatus != "done"]` (direct immediate target styling)
- On language change, the graph is reloaded and elements are re-added.
- There are two separate change handlers attached to the same `#settingsLangSelect` element.

Code evidence (duplicate listeners on language select):

```1369:1383:app/templates/project.html
// language change handled by Settings dropdown
document.getElementById('settingsLangSelect')?.addEventListener('change', async (e)=>{
  const lang = e.target.value || '';
  localStorage.setItem('displayLang', lang);
  if (lang) await ensureTranslations(lang);
  graph = await fetchGraph(lang);
  cy.elements().remove();
  cy.add(toElements(graph));
  cy.layout({ name: 'preset' }).run();
  cy.fit();
  // Recompute edge path colors based on current graph
  try { recomputePriorityPaths(); } catch {}
  // Re-apply LOD and filters after reload
  try { applyLOD(); applySearchAndFilter(); } catch {}
});
```

```2099:2112:app/templates/project.html
// Settings: wire Language select and sync with toolbar
(function wireSettingsLanguage(){
  const sSel = document.getElementById('settingsLangSelect');
  if (!sSel) return;
  // initialize from saved
  const saved = localStorage.getItem('displayLang') || '';
  sSel.value = saved;
  sSel.addEventListener('change', async (e)=>{
    const lang = e.target.value || '';
    localStorage.setItem('displayLang', lang);
    if (lang) await ensureTranslations(lang);
    graph = await fetchGraph(lang);
    cy.elements().remove(); cy.add(toElements(graph)); cy.layout({ name: 'preset' }).run(); cy.fit();
  });
})();
```

Observation:
- The second listener reloads the graph but does NOT call `recomputePriorityPaths()` nor re-apply filters/LOD.
- If the second listener runs after the first, it effectively resets `pathPriority` to `none` on all edges (newly added elements) leaving only direct target-based styling active. This matches the bug: only edges leading directly into a priority target remain colored; the cascade is gone.

### Hypothesis (Root Cause)

Duplicate `change` handlers for `#settingsLangSelect` cause the final graph state after a language switch to skip `recomputePriorityPaths()`. As a result, `edge.data('pathPriority')` is not set, and cascade coloring disappears.

### Acceptance Criteria

- After switching language, cascade coloring must appear on the full upstream path toward not-done high/critical nodes (same as initial page load).
- No duplicate listeners on `#settingsLangSelect`.
- LOD and search-filter remain applied after language switch.
- No regression to translation flow or node labels.

### Implementation Plan

- Unify language change logic into a single function, e.g., `handleLanguageChange(lang)`:
  - Persist to `localStorage`.
  - Ensure translations (best-effort).
  - Reload graph data with `fetchGraph(lang)` and re-add elements.
  - Call `recomputePriorityPaths()`.
  - Re-apply `applyLOD()` and `applySearchAndFilter()`.
- Remove/disable the duplicate listener in `wireSettingsLanguage()` or make it call the unified handler only; avoid re-binding the same event twice.
- Optional: call `refreshEdgeTargetFlags` for all nodes after reload for consistency (though `toElements` already sets `targetStatus`/`targetPriority`).
- Keep code DRY: a single place handles both initial value sync and `change` event wiring.
- No backend changes required.

### Manual Testing (UI)

- Open a project page.
- Verify cascade coloring works initially.
- Open Settings sidebar, use `Language` select to switch to a non-empty language (e.g., `en`).
- Expected: Graph reloads, cascade coloring highlights all upstream paths to not-done high/critical nodes, not only edges directly to the priority target.
- Toggle language back and forth; verify behavior remains consistent.
- Change a node’s priority and status; verify `recomputePriorityPaths()` continues to update coloring.
- Verify that search filter and LOD are still applied after language switch.

### Risks & Mitigations

- Event order differences across browsers: consolidate to one handler to avoid race.
- Performance on large graphs: keep recomputation within the same tick; avoid double reloads.

### Rollout & Monitoring

- Ship as a single frontend edit in `project.html`.
- Smoke test with a project containing multiple levels of dependencies and mixed priorities/statuses.

### Tasks (checklist)

- [x] Consolidate language change handling into one function.
- [x] Remove duplicate `change` listener in `wireSettingsLanguage()` or refactor it to call the unified handler.
- [x] After reload: call `recomputePriorityPaths()`, `applyLOD()`, `applySearchAndFilter()`.
- [ ] Quick QA on language switch and cascade coloring.
- [ ] Update roadmap with results and any follow-ups.

### Implementation Notes (2025-09-01)

- Added `handleLanguageChange(lang)` in `app/templates/project.html` and wired `#settingsLangSelect` to this function only.
- Removed the second direct `change` handler which previously reloaded the graph without recomputing cascade coloring.
- Verified no linter issues after edits.

### Compliance

- Adhere to SOLID, DRY, KISS, Separation of Concerns, Single Level of Abstraction, Clean Code Practices.
- Maintain UI/UX principles: User-Friendly, Intuitive, Consistency, Accessibility, Feedback, Simplicity, Aesthetic & Modern, Performance, Responsive Design.


