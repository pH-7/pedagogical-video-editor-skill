<div align="center">
  <img src="assets/logo.svg" alt="Pedagogical Video Editor logo" width="180" />
  <h1>Pedagogical Video Editor</h1>
  <p><strong>Make educational videos clearer, more engaging, and easier to edit with Codex.</strong></p>
  <p>A reusable Codex skill for planning, editing, previewing and reviewing long-form lessons, explainers, tutorials and Shorts.</p>
  <p><a href="#quick-start">Quick start</a> · <a href="#what-it-does">Features</a> · <a href="#how-it-works">Workflow</a> · <a href="#about-the-author">Author</a></p>
</div>

---

## Why this skill?

Good educational editing should support the explanation, not distract from it. This skill combines editorial guidance with a local FFmpeg/Python pipeline to build videos with purposeful cuts, restrained zooms, visual explanations and sound design.

It focuses on **long-form retention without constant effects**. Codex can inspect supplied footage, transcripts and authorised reference videos, then help you prepare and review an editable JSON edit plan.

> **Current scope:** This is an assisted editing workflow, not a one-click autonomous video editor. The Python renderer executes a prepared plan; Codex or a human must still make and verify editorial decisions. Automatic speech transcription and AI-generated illustrations are not bundled.

## What it does

| Capability | Included |
| --- | --- |
| Video analysis | Detect silence, scene changes and audio levels |
| Timeline editing | Source cuts, previews and H.264 MP4 exports |
| Visual storytelling | Restrained punch-ins, text cards and image overlays |
| Sound design | Optional music and timed sound effects supplied by you |
| Captions | Use supplied SRT files; optional burned-in subtitles |
| Reference analysis | Measure broad pacing traits from videos you may use |
| Quality checks | Inspect technical properties, loudness, black frames and freezes |
| Editor hand-off | JSON edit plan, technical reports and cut-based FCPXML |

The FCPXML timeline contains source cuts, not fully editable recreations of every overlay or sound treatment. Read the [limitations](references/limitations.md).

## Quick start

**Requirements:** [Codex](https://openai.com/codex/) with local file access, Python 3.10+, FFmpeg and FFprobe.

On macOS:

```bash
brew install ffmpeg
mkdir -p ~/.agents/skills
git clone https://github.com/pH-7/pedagogical-video-editor-skill.git ~/.agents/skills/pedagogical-video-editor
python3 ~/.agents/skills/pedagogical-video-editor/scripts/pve.py doctor
```

Restart Codex, then invoke `$pedagogical-video-editor`. Keep your original recording somewhere safe and supply its local file path. See the [setup guide](references/setup.md) for other operating systems.

## How it works

**1. Prepare and analyse footage**

From the skill directory:

```bash
python3 scripts/pve.py init --project ./demo --source /path/to/recording.mp4 --language fr
python3 scripts/pve.py analyze --project ./demo
```

**2. Plan the edit**

Optionally add `demo/transcript.srt`, timed against your original recording. Review the footage and the [editorial guide](references/editorial-guide.md), then adjust `demo/edit_plan.json` using the [plan schema](references/plan-schema.md). Decide where a cut, diagram, zoom or sound actually helps the viewer.

**3. Preview, render and review**

```bash
python3 scripts/pve.py render --project ./demo --preview
python3 scripts/pve.py qc --project ./demo --preview
python3 scripts/pve.py render --project ./demo
python3 scripts/pve.py qc --project ./demo
python3 scripts/pve.py export-fcpxml --project ./demo
```

Your output is `demo/master.mp4`. Always watch the full result and verify dialogue, subtitles, timing and asset permissions before uploading.

### Prompt for Codex

> Use $pedagogical-video-editor to edit my French educational video. Analyse the footage and transcript, propose meaningful cuts and subtle zooms, and add diagrams or sound effects only when they improve understanding. Preserve my voice and natural delivery. Render a preview, review the result, then export the final MP4 and editable plan.

## Tests

```bash
python3 scripts/test_pipeline.py
```

The synthetic smoke test exercises the local pipeline, but cannot guarantee production quality or compatibility with every video. The actual render must still be reviewed.

## About the author

<a href="https://github.com/pH-7"><img src="https://github.com/user-attachments/assets/5d82ee36-78a2-41bd-8c14-9b80929105d5" width="105" align="right" alt="Pierre-Henry Soria" /></a>

**[Pierre-Henry Soria](https://pierrehenry.dev)** is a senior software engineer, open-source contributor and educational content creator. His work spans product engineering, AI, software architecture and developer tools. He also creates programming courses and videos, sharing practical techniques that help developers learn and build better software.

[Website](https://pierrehenry.dev) · [GitHub](https://github.com/pH-7) · [YouTube](https://www.youtube.com/@pH7Programming) · [LinkedIn](https://www.linkedin.com/in/ph7enry/)

<br clear="right" />

## Usage and rights

Use only footage, music, sound effects, illustrations and reference material that you own or are authorised to use. Analyse other creators for general educational editing principles, not to reproduce their exact visual identity.

This repository does not currently include a `LICENSE` file. Public visibility does not itself grant permission to reuse or redistribute the code. An open-source licence can be added once its terms have been chosen.
