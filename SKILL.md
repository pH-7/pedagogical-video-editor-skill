---
name: pedagogical-video-editor
description: Analyse, plan, edit, preview, and quality-check engaging educational videos from supplied footage, transcripts, brand assets, and optional reference videos. Use for long-form lessons, talking-head explainers, course videos, and educational shorts where pacing, purposeful cuts, restrained zooms, captions, diagrams, sound design, and editable hand-off files matter.
---

# Pedagogical Video Editor

Build an intelligible, human-reviewable edit. Treat the included pipeline as deterministic production infrastructure, not as a substitute for editorial judgement.

## Start here

1. Confirm the requested format, audience, language, target duration, delivery resolution, and supplied source files. Never download or imitate a creator's proprietary video without permission.
2. Run `python3 scripts/pve.py doctor`. If FFmpeg is missing, stop and give the setup steps from [setup.md](references/setup.md).
3. Create a project: `python3 scripts/pve.py init --project <project-dir> --source <video> --language fr`.
4. Put an existing `.srt` transcript at `<project-dir>/transcript.srt`, or follow the optional transcription instructions in [setup.md](references/setup.md). Do not pretend transcription happened when it did not.
5. Run `analyze`. For one or more authorised reference videos, also run `reference` and use the report to infer broad pacing patterns, never to clone a creator's identity.
6. Read `analysis.json`, the transcript, and [editorial-guide.md](references/editorial-guide.md). Revise `edit_plan.json` deliberately: every cut, zoom, visual, caption, music cue, and sound effect must clarify or sustain attention.
7. Run `render --preview`, inspect the entire preview, revise the plan, then render the master. Run `qc` on the master and resolve material failures before delivery.
8. Deliver the master, preview, captions, plan, analysis, QC report, and `timeline.fcpxml`. Clearly distinguish tested output from suggestions or missing optional capabilities.

## Editorial rules

- Preserve meaning, chronology, speaker intent, and natural breathing room. Never remove a pause merely because it is silent.
- Prefer invisible edits. Use jump cuts when they remove genuine friction; cover disruptive cuts with relevant B-roll, diagrams, screen detail, or a motivated punch-in.
- Use motion sparingly. A subtle 1.04–1.10 punch-in can mark emphasis; return to neutral. Avoid constant zoom oscillation and novelty transitions.
- Change the visual state when the learning state changes: new claim, example, contrast, definition, process, or recap. Do not add decoration to hit a cadence quota.
- Educational visuals must carry information: label, comparison, step, evidence, spatial relation, or recall cue. Verify facts and rights for every asset.
- Sound effects should be quiet, short, and semantically motivated. Duck music under speech. Do not mask consonants or create loudness surprises.
- For French, preserve accents, apostrophes, punctuation, speaker register, and appropriate line breaks. Do not translate unless requested.
- Analyse reference material by measurable traits such as pause handling, shot length, density of visual aids, caption treatment, and audio dynamics. Do not reproduce logos, signature graphics, music, wording, or a living creator's recognisable style.

## Plan and pipeline

Read [plan-schema.md](references/plan-schema.md) before making non-trivial edits. The starter plan is intentionally conservative. Update it from semantic analysis of the transcript and footage.

Useful commands:

```bash
python3 scripts/pve.py analyze --project <project-dir>
python3 scripts/pve.py reference --project <project-dir> --videos <ref1> <ref2>
python3 scripts/pve.py render --project <project-dir> --preview
python3 scripts/pve.py render --project <project-dir>
python3 scripts/pve.py qc --project <project-dir>
python3 scripts/pve.py export-fcpxml --project <project-dir>
```

The pipeline preserves editable decisions in JSON/SRT and exports a cut-based FCPXML timeline. Burned-in graphics, animated zooms, mixing, and some generated treatments remain flattened in the rendered video; document that limitation.

## Review gates

Before claiming completion, verify:

- the archive or project paths exist and outputs open;
- duration, dimensions, frame rate, audio stream, and language match the brief;
- cuts do not clip words or gestures;
- captions are accurate, readable, and within safe margins;
- every visual and sound cue is relevant, licensed, and timed correctly;
- speech remains clear and the QC report has no unexplained failure;
- preview and master were produced from the same current plan;
- editable source decisions and limitations are included.

Read [limitations.md](references/limitations.md) when scoping or handing off work.
