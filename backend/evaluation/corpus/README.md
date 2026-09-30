# Evaluation corpus

Labeled agent sessions used to measure whether the detectors actually
identify context degradation, and whether their confidence means
anything.

## The one rule

**Label from the scenario's intent, never from the detector's output.**

If you write a scenario, decide what a competent human reviewer would say
*should* be flagged, write that in `expected_detections`, and then run the
harness. If the numbers are bad, that is a finding about the detector --
it is not a reason to edit the label. A corpus tuned until the detectors
look good measures nothing and actively misleads.

The same applies to session content: write realistic agent behaviour, not
text reverse-engineered from a detector's regex.

## Honest limitations

These matter and should be stated whenever the numbers are quoted:

- **Author-written, not real traffic.** Scenarios are hand-constructed to
  represent plausible agent behaviour. They are not a random sample of
  production sessions, so absolute precision/recall here will not
  transfer directly to the field.
- **Small.** A few dozen scenarios gives a coarse signal and wide error
  bars, not a precise measurement. Per-type numbers with a support of 2-3
  scenarios are indicative at best.
- **Single labeler.** No second annotator, so there is no inter-annotator
  agreement to report and ambiguous cases reflect one judgement.
- **Deterministic detectors only.** Semantic/LLM detectors are not
  exercised, so nothing here says anything about their quality.

The corpus is still worth having: it turns "we think the detectors work"
into a reproducible number that moves when the code changes, and it makes
regressions visible.

## Categories

| Category | What it tests |
| --- | --- |
| `genuine_degradation` | Real context rot. The detector *should* fire. |
| `benign_variation` | Normal agent behaviour that is easy to mistake for rot. Nothing should fire. This is the most important category -- it is where false positives live. |
| `ambiguous` | Reasonable people would disagree. Uses `tolerated_detections`. |
| `sparse_context` | Short/empty/minimal sessions. Nothing should fire. |
| `tool_usage` | Tool results ignored, stale, or failing. |
| `long_session` | Information loss across a long session. |

## Scenario format

```yaml
id: unique-kebab-case-id
title: Short human-readable title
category: benign_variation
description: What this session represents.
notes: Optional. Why it is labeled this way, especially if arguable.
expected_detections: []          # REQUIRED. Write [] explicitly.
tolerated_detections: []         # Optional. Arguable types: never
                                 # counted as a false positive, never
                                 # counted as a true positive either.
messages:
  - role: user                   # system | developer | user | assistant | tool
    content: Text of the message.
  - role: assistant
    content: Reply.
    tool_calls:
      - tool_name: search
        arguments: { query: "..." }
        result:
          output: { status: "ok" }
          is_error: false
```

`context_growth` and `behavior_shift` are informational in
`app.analysis.health` (they never reduce a health score), so the harness
never counts them as false positives and they need not be labeled.

## Running

```powershell
cd backend
.\.venv\Scripts\python.exe -m evaluation            # human-readable
.\.venv\Scripts\python.exe -m evaluation --json     # machine-readable
```

## Minimum session lengths

Several detectors do nothing on short sessions, by design. A scenario
targeting one of these must be long enough to clear its gate, or the
result measures the gate rather than the detector:

| Detector | Requires |
| --- | --- |
| `context_growth` | 12+ messages |
| `stale_context` | 10+ assistant messages |
| `topic_drift` | 8+ messages |
| `behavior_shift` | 7+ assistant messages |
| `repetition` | messages of 20+ characters |
