# In-app user guidance (English) — reviewed plan

> **Status**: Reviewed; waiting for approval before writing to the live instance  
> **Updated**: 2026-08-19  
> **User-facing language**: **English only** for banners, prompt suggestions, model descriptions, overlays, watermarks, and any other instructional UI copy  
> **Internal notes** (this file, PR, admin chat): Chinese is fine  
> **Related**: `docs/open-webui-openrouter-image-continuity-plan.md`

---

## Review of the previous plan

| Previous draft | Verdict |
|----------------|---------|
| 3–4 simultaneous banners (overview + reasoning + deep wait + details) | **Too noisy.** Banners are global and always on. Four bars fight simplicity. Keep **one** compact banner. |
| Deep Research wait time as its own warning banner | **Wrong surface.** It shows even when the user is chatting with Sol/Opus. Put wait time on the **Deep Research model description**. |
| Prompt suggestions as “quick search / draw image” chips | **Risky.** Suggestions send a message on the **currently selected** model. They do **not** switch models. A “today’s news” chip on Sol Pro teaches the wrong habit. Titles must say **which model to pick first**, or skip search/image chips until that is obvious. |
| Chinese banner copy | **Rejected.** All instructional UI copy is **English**. |
| Keep existing banner and add more | **Replace it.** Current copy is English but incomplete and misspelled (`resoning`). Path is useful: input box Valves → Reasoning depth → xhigh. |
| Pending overlay / response watermark | **Skip.** Overlay only hits `pending` users. Watermark repeats on every reply. |
| Rename models in the picker to 快搜/作图 | **Defer.** Exact display names already appear in the UI; banners should match them. Rename is a separate product change. |
| Restore OR Web Tools / Web Search in copy | **Never.** Conflicts with Plan A. |

### What still holds

- **Game changers** for a normal user: (1) pick the right model, (2) raise **Reasoning depth** for hard work, (3) wait on Deep Research, (4) switch to an image model before asking for pictures.
- **Banners** are the right global surface. **Model descriptions** are the right per-model surface.
- Live API: `POST /api/v1/configs/banners` with `{"banners":[...]}`. Content is **HTML only**.

### Live instance (today)

- One dismissible info banner: `highest resoning: 'valves' at the inputbox >> 'reasoning depth' >> 'xhigh'`
- User valve label is **Reasoning depth** (`none` … `xhigh`). User setting overrides the site default.
- Pinned: Sonar Pro Search, Sonar Deep Research, Claude Opus 5, GPT-5.6 Sol Pro — **no descriptions**
- `prompt_suggestions`: empty
- `DEFAULT_MODELS` still points at **non-pipe** ids (`anthropic/claude-sonnet-4.6`, …). New chats may not land on a Pipe model. Fixing that is **out of this copy pass** unless approved.

---

## Design rules for user-facing copy

1. **English only.** Model names match the UI: `Sonar Pro Search`, `Sonar Deep Research`, `GPT-5.6 Sol Pro`, `Claude Opus 5`, `Nano Banana Pro`, `GPT Image 2`.
2. **One global banner.** Scannable in two lines. `type: info`. New `id` so anyone who dismissed the old banner sees this once.
3. **Per-model facts live in descriptions**, not extra banners.
4. **Do not instruct users to open hidden Integrations** (OR Web Tools / OR Image Gen / Web Search).
5. **Compact HTML** (no extra blank lines — OWUI treats newlines as `<br>`).
6. **Dismissible: true** so power users can hide it; changing `id` re-shows after a copy revision.

---

## Surfaces and proposed English copy

### 1. General UI Banner (primary) — **one bar**

- **id**: `usage-guide-v2`
- **type**: `info`
- **title**: `How to use this workspace`
- **dismissible**: `true`
- **content** (HTML, keep compact):

```html
<b>Chat</b> GPT-5.6 Sol Pro or Claude Opus 5 · <b>Quick search</b> Sonar Pro Search · <b>Deep report</b> Sonar Deep Research (2–10 min, keep this tab open) · <b>Images</b> switch to Nano Banana Pro or GPT Image 2 first<br>
Hard problems: input-box <b>Valves</b> → <b>Reasoning depth</b> → <b>high</b> or <b>xhigh</b>. Easy tasks: <b>low</b> / <b>medium</b> (faster). Do not use Sonar for everyday chat.
```

This **replaces** the current banner. Reasoning path matches the live UserValves title **Reasoning depth**.

### 2. Model descriptions (per-model, English)

| UI name | `meta.description` |
|---------|-------------------|
| Perplexity: Sonar Pro Search | Quick web search with citations. For chat, writing, or reasoning use GPT-5.6 Sol Pro or Claude Opus 5. |
| Perplexity: Sonar Deep Research | Long sourced reports. Typically 2–10 minutes — keep this tab open; do not refresh or switch models. |
| OpenAI: GPT-5.6 Sol Pro | Default chat and hard reasoning. For difficult tasks, set Valves → Reasoning depth to high or xhigh. Not for live web search. |
| Anthropic: Claude Opus 5 | Strong reasoning and long writing. Not live-web; use Sonar Pro Search for current news. |
| Google: Nano Banana Pro (Gemini 3 Pro Image) | Primary image model. Switch here before asking for pictures. Multi-turn edits may drift slightly. |
| OpenAI: GPT Image 2 | Alternate image model. Switch here before asking for pictures. |

Exact Banana display name should be copied from Admin once at apply time (instance may show `Nano Banana Pro` vs `Gemini 3.1 Flash Image`).

### 3. Prompt suggestions (optional, English) — teach **switch first**

Empty-chat chips send text to the **current** model. Every search/image chip must say which model to select.

| `title` | `content` |
|---------|-----------|
| `["Quick search", "Select Sonar Pro Search first"]` | After you select Sonar Pro Search, summarize today’s most important AI news in a few sentences with sources. |
| `["Deep report", "Select Sonar Deep Research first"]` | After you select Sonar Deep Research, write a sourced industry brief on [topic]. Keep this tab open; it can take 2–10 minutes. |
| `["Images", "Select Nano Banana Pro first"]` | After you select Nano Banana Pro, generate a clean product render of [object] on a white background. |
| `["Hard reasoning", "Raise Reasoning depth"]` | On GPT-5.6 Sol Pro or Claude Opus 5, set Valves → Reasoning depth to high or xhigh, then [task]. |

If that feels heavy, **skip suggestions** and ship banner + descriptions only.

### 4. Out of scope for this pass

- Changing default / pinned models
- Renaming models in the picker
- Model-conditional banners (not supported)
- Filter popups, watermarks, pending overlay

---

## Rollout (after approval)

1. **UI-1**: `POST /api/v1/configs/banners` with the single `usage-guide-v2` banner (drop the old id).
2. **UI-2**: Set descriptions on the four pinned models (+ two image models if still public).
3. **UI-3** (optional): English prompt suggestions as above.
4. Spot-check as a normal user: banner English, dismiss, descriptions in the model menu, no Chinese instructional text.

Script (when executing): `scripts/apply_ui_guidance_banners.py` — banners + descriptions only; **merge** nothing that touches Pipe `API_KEY`.

---

## Approval checklist

- [ ] Ship **one** English banner as in §1 (recommended)
- [ ] Add English **model descriptions** (§2)
- [ ] Prompt suggestions: yes / no
- [ ] Apply via API after approval (no Admin copy-paste required)

Do not change live banners, suggestions, or descriptions until this is approved.
