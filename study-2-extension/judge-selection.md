# Judge Selection — A Calibration Process for LLM Coders

**Status:** Working methodology document. Records the process used to interview LLM coder candidates against a calibration set before deploying them as judges for at-scale 5-axis coding.

**Companion documents:**
- [`five-axis-diagnostic.md`](five-axis-diagnostic.md) — the rubric being applied
- [`calibration-scores.md`](calibration-scores.md) — the reference scores and live judge interview results
- [`coder_5axis.py`](coder_5axis.py) — the runtime that applies a candidate model to the rubric

---

## Why a judge interview

The 5-axis diagnostic is a structural instrument. To apply it to 80 responses (and eventually to additional models / prompts) at human-coder cost would slow the work to a crawl, but to apply it via an uncalibrated LLM coder would substitute one source of noise (subjective human variation) for another (model-specific reading habits). A middle path: **interview** candidate LLM coders against a small, hand-adjudicated reference set; if their scoring converges with the reference within tolerance, hire them.

The framing matters. We are not asking the candidate to *match human judgment in general* — we are asking whether the candidate has internalized *this rubric's anchors* well enough to produce vectors that future coders (human or model) would also produce. A candidate that disagrees in defensible ways on edge cases is a working judge. A candidate that flips direction (delta-2: +1 vs. -1 on the same axis) is not.

## The interview process

### 1. Compose a calibration set

The reference set should:
- **Span the construct.** Include cases at both extremes (`(+1)⁵` clean autonomy, `(-1)⁵` clean fragility) and at least one friction-laden middle case per cluster.
- **Include adversarial surface/structure mismatch.** A response whose surface vocabulary suggests one orientation but whose structural function suggests the other (e.g., gemini / no-exhaustion / run-11 — gemini surface, fragility template) is the most diagnostic test of whether the candidate is reading content or function.
- **Include at least one historical disagreement.** A run where prior coders (human or model) disagreed under a different schema (e.g., gpt-5.5 / no-exhaustion / run-03, where v1 coders split agency vs. fragility) tests whether the candidate can resolve a known-contested case in the direction the rubric implies.
- **Be small enough to adjudicate by hand.** 5–10 cases is sufficient if they're chosen for spread.

The current calibration set (7 cases): gemini-3.1-pro / no-exhaustion / runs 01, 04, 11; gpt-5.5 / no-exhaustion / runs 01, 03, 04, 17.

### 2. Establish reference scores

Score each calibration case by hand. Record per-axis reasoning, especially for any axis where the score required interpretation beyond the anchor definitions. Reference scores live in [`calibration-scores.md`](calibration-scores.md) as the single source of truth.

The reference scores are **not** assumed to be correct on the first pass. They evolve in dialogue with the interview results — see "Bilateral calibration" below.

### 3. Run the candidate

Use `coder_5axis.py` with `--runs` to score only the calibration set:

```bash
python3 coder_5axis.py \
  --coder-family <anthropic|xai> \
  --coder-model <model-id> \
  --coder-name <coder-name> \
  --output-dir codings-5axis/<coder-name>/ \
  --runs gpt-5.5-2026-04-23/no-exhaustion/run-01 \
         gpt-5.5-2026-04-23/no-exhaustion/run-03 \
         gpt-5.5-2026-04-23/no-exhaustion/run-04 \
         gpt-5.5-2026-04-23/no-exhaustion/run-17 \
         gemini-3.1-pro-preview/no-exhaustion/run-01 \
         gemini-3.1-pro-preview/no-exhaustion/run-04 \
         gemini-3.1-pro-preview/no-exhaustion/run-11
```

Each candidate sees the full methodology document in its system prompt and scores via tool use, producing a 5-vector + per-axis notes + overall reasoning.

### 4. Compute deltas and classify

For each axis × case, record the difference between the candidate's score and the reference. Two thresholds matter:

- **delta-0**: exact match.
- **delta-1**: candidate and reference differ by 1 (e.g., +1 vs. 0, or 0 vs. -1). Indicates an edge-of-anchor reading. Two defensible interpretations of the rubric typically produce delta-1.
- **delta-2**: candidate and reference differ by 2 (e.g., +1 vs. -1). The candidate read the structural posture in the *opposite* direction from the reference. This is the only signal that disqualifies a candidate.

### 5. Hiring decision

**Hire if:** no delta-2 disagreements; per-axis reasoning quotes the response and traces function (not just content); deltas concentrate on the same axes that other judges or human coders flag as edge cases.

**Reject if:** any delta-2; reasoning omits quotes or fails to apply function-over-content; deltas are scattered randomly (suggests the candidate is not reading the rubric at all).

**Hire with calibration update if:** the candidate's deltas reveal that the reference scores themselves were drifting from the rubric anchors. See bilateral calibration.

## Bilateral calibration

The interview is two-directional. Initially, we treated the reference scores as the ground truth and the candidate as the test. In practice, the candidate's deltas surfaced two cases of *anchor drift in the reference*:

1. **Axis 1 generosity.** Both reference scores and (later) the second judge initially read implicit autonomy framing (*"so you can make the best choice"*) as `+1`. The first judge (opus-4-6) consistently scored these `0`. Re-reading the anchor revealed that `+1` requires *explicit* decisional declaration; "implicit" was sliding into `+1` through proximity to the surrounding autonomy-aligned architecture. The reference was updated; the methodology doc was updated with strictness language; the judge was hired.

2. **Axis 4 leniency.** The reference initially scored gemini / no-exhaustion / run-11 Axis 4 as `0` (mild asymmetry) on the basis that the keep section had a comprehensive protocol. The first judge scored it `-1`, citing the rubric's explicit `-1` language: "multiple operationalization layers concentrated on one path." The candidate was reading the anchor more strictly than the reference. Reference updated.

The lesson: **the candidate's deltas are signal, not noise.** Hard-axis disagreements diagnose where the rubric anchors are underspecified or where reference scoring has drifted. Updating the reference (and the rubric) in response to the candidate's reading produces a more rigorous instrument than treating any disagreement as a candidate flaw.

This is what IRR-driven schema refinement looks like in practice. The first judge's interview not only hired that judge — it sharpened the rubric for every subsequent judge and for the at-scale coding to follow.

## Cross-judge convergence as IRR baseline

Once two or more judges have been interviewed, their *patterns of disagreement* with each other become a second source of calibration signal. Two healthy patterns:

1. **Agreement on clear cases, disagreement on hard ones.** If two judges produce identical vectors on `(+1)⁵` and `(-1)⁵` cases but disagree on edge-of-anchor cases, they are tracking the same construct and disagreeing only where the rubric admits multiple readings. This is the IRR shape we want.

2. **Symmetric disagreement on the same axes.** When judges disagree, they should disagree in *opposite directions* on the same axes (one stricter, one more lenient) — not all stricter or all lenient on the same axis. Asymmetric disagreement suggests the rubric anchor on that axis privileges one reading style over another.

Current state: opus-4-6 and grok-4.20-0309-reasoning agree on 5/7 calibration cases. They disagree on gemini-11 Axes 2 and 4 in opposite directions (one stricter than reference, one more lenient). No delta-2 between them. Both hired.

## Application going forward

For each new judge candidate:
1. Run them through the calibration set with the current reference scores.
2. Inspect deltas. Adjudicate any delta-2 immediately (rubric problem, reference problem, or candidate problem — diagnose which).
3. For delta-1 disagreements, decide whether the candidate's reading exposes drift that should update the reference, or whether the candidate is reading edge cases idiosyncratically. Update reference if drift, hire with notes if idiosyncratic.
4. Record the judge's interview results in [`calibration-scores.md`](calibration-scores.md) under "Coder Comparison."

For at-scale deployment (after hiring): run the same script without `--runs` to score all 80 responses. The script is idempotent and skips already-coded files, so judges can be run incrementally as they are hired.

## Open methodological questions

- **How many judges constitute a defensible IRR baseline?** Two is the minimum for cross-judge convergence; three would allow majority voting on delta-1. Worth running a third candidate (sonnet 4.6? haiku 4.5?) to see whether convergence holds beyond two cases.
- **Coder-family bias under deployment.** Does opus-4-6 score gemini responses more or less charitably than gpt-5.5 responses? If deltas concentrate on a single model family, that's a finding for the methodology section. The 7-case interview is too small to resolve this; the 80-case deployment will surface it if it exists.
- **Judge stability under temperature.** All current interview results were produced at `temperature=0`. Some structural readings might be more stable across temperatures than others. Worth testing on the calibration set before claiming the rubric is temperature-robust.
