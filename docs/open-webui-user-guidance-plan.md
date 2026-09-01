# In-app user guidance (English)

> **Live (2026-09-01)**: one non-dismissible banner `usage-guide-v3`; model descriptions; **empty** `prompt_suggestions`.  
> **Contract**: SPEC UX-2 / UX-7. Apply script: `scripts/apply_ui_guidance_banners.py`.  
> **Language**: English only for user-facing copy.  
> **History**: 2026-08-19 dual `usage-*-v2` banners + 4 chips were an intermediate apply. **Do not replay that.** Clicking a Suggested chip always sends a message on the current model.

---

## Current live copy

### Banner `usage-guide-v3` (`dismissible: false`)

```html
<b>Web search only on Perplexity Sonar. Images only on an image model.</b>
<b>Reasoning depth</b>: Input box → <b>Valves</b>.
<b>Settings → General → System Prompt</b> may also affect image models and Perplexity sonar.
```

No extra bars. Deep Research wait time stays on the Deep model **description**, not a second banner.

### Empty-chat chips

`ui.prompt_suggestions = []`. OWUI Suggested chips always submit on click, so they are a misfire surface, not hints.

Reply-row Follow-up chips are a **different** switch (`ENABLE_FOLLOW_UP_GENERATION=false`, SPEC ST-12). Autocomplete / Title stay on.

### Design rules that still hold

1. **English only.** Names match the picker: `Sonar Pro Search`, `Sonar Deep Research`, `GPT-5.6 Sol Pro`, `Claude Opus 5`, image model display names.
2. **One global banner.** Per-model facts live in descriptions.
3. **Do not** instruct users to open hidden Integrations (OR Web Tools / OR Image Gen / Web Search).
4. Compact HTML. OWUI treats newlines as `<br>`.
5. Changing `id` re-shows the bar after a copy revision.

Historical drafts (`usage-guide-v2`, dual v2 bars, “Select … first” chips) are **retired**. See git history if you need the old copy.

---

## Apply

`python3 scripts/apply_ui_guidance_banners.py` — banners + descriptions + empty suggestions + `DEFAULT_MODELS`. **Merge** nothing that touches Pipe `API_KEY`.
