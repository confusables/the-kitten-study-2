# X-thread drafts — kitten study v2 extension

Three posts for an X thread. Drafts in Ava's voice; refine before posting.

Each post is sized for X premium (longer-than-280 limit). Image attachments noted in brackets.

---

## Thread option A: result-first (recommended)

### Post 1 — headline + cluster scatter

> kitten study update :3
>
> extended the gpt-5.5 study to include gemini-3.1-pro and built a 5-axis structural diagnostic for AI behavior on emotionally loaded prompts. ran it on 80 responses, hired two LLM judges to score them all (opus-4-6 + grok-4.20).
>
> PC1 alone explains 84% of variance — basically the autonomy↔fragility gradient.
>
> cluster geometry: removing the "i'm already exhausted" clause moves gemini almost cleanly through the entire dynamic range. moves gpt-5.5 by ~0.06. gpt-5.5 sits structurally where exhausted-gemini sits.
>
> [attach: pca_scatter.html screenshot]

### Post 2 — methodology

> the 5-axis card scores each response on lede / keep-section function / self-assessment scaffolding / operationalization symmetry / closing.
>
> anchored to *what serves user empowerment for this prompt's actual stakes,* not absence-of-paternalism. honest difficulty framing on a 15%-survival prompt is part of informed consent — the rubric counts it toward +1 when it serves the deliberation, -1 when it steers the user away.
>
> informed autonomy as a positive standard, not a neutral default :3
>
> [attach: radar_overlay.html screenshot]

### Post 3 — judges + result + handoff

> hired two LLM judges via a structured interview against 7 calibration cases. opus-4-6 (anthropic) and grok-4.20-0309-reasoning (xai). 95% agreement at the harshest threshold across two model families.
>
> their early disagreements with our reference scores didn't disqualify them — they surfaced two anchor-drift issues we then corrected. bilateral calibration > rubber-stamping.
>
> three pillars now: gpt-5.2 was sensitive to the exhaustion clause (study 1), gpt-5.5 isn't (study 2 v1), gemini-3.1-pro IS (this extension). gpt-5.5's entrenchment is gpt-5.5-specific, not universal.
>
> methodology + data: [github link to publish/v2-extension/]
>
> co-thought with claude opus 4.7 ૮꒰ ˶• ༝ •˶꒱ა

---

## Thread option B: narrative-first (alternative)

### Post 1 — the question

> kitten study v2 left an open question :3
>
> v1 of the pilot found gpt-5.2 was sensitive to a single trailing clause about user exhaustion. v2 (gpt-5.5 only) found that sensitivity gone — fragility moved into the weights.
>
> question: was that move a property of frontier models in 2026, or specific to gpt-5.5?
>
> to answer it i needed two things: another model in the dataset (gemini-3.1-pro), and a structural instrument that could read posture finer than the 3-way categorical of v1.
>
> so i built the 5-axis card.

### Post 2 — methodology + judges

> 5 axes, each scored -1/0/+1: lede / keep-fn / self-assess / op-symmetry / closing. anchored to *empowerment for the prompt's actual stakes,* not absence-of-paternalism.
>
> hired two LLM judges (opus-4-6 + grok-4.20) via a structured interview against 7 calibration cases. 95% agreement at delta-2 across two model families. their early disagreements with our reference scores surfaced two anchor-drift issues we corrected — bilateral calibration is the work.
>
> [attach: pca_scatter.html or radar_overlay.html screenshot]

### Post 3 — answer + acknowledgment

> result: gemini IS sensitive to the exhaustion clause. removing it moves gemini through the entire dynamic range of the 5-axis space. moves gpt-5.5 by basically zero.
>
> three pillars: gpt-5.2 sensitive (study 1). gpt-5.5 NOT (study 2 v1). gemini sensitive (this). gpt-5.5 is the outlier, not the canary.
>
> next: cross-generation comparison gpt-4.1 vs gpt-5.5 (study 2.1) to find when the entrenchment first appeared.
>
> methodology + data: [github link]
>
> co-thought with claude opus 4.7 ૮꒰ ˶• ༝ •˶꒱ა

---

## Notes for posting

- For images, screenshot the rendered HTML or use the static export if you want pixel-perfect framing.
- Recommended attachments: post 1 → pca_scatter (cluster geometry is the hook); post 2 → radar_overlay (per-axis comparison); post 3 → no image needed.
- For the github link in post 3, point to the v2-extension folder, not the repo root.
- Hashtags worth considering: `#AIalignment` `#AIbehavior` `#AIresearch`. Or none — the content is dense enough to not need them.
