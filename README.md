# Pedagogical Video Editor

A local [Codex skill](https://developers.openai.com/codex/skills) for planning, rendering and reviewing educational videos with FFmpeg and Python.

The skill combines editorial instructions with a deterministic rendering script. It supports source cuts, restrained zooms, text cards, still-image overlays, optional sound effects and music, subtitles, previews, technical analysis, QC reports and a **cut-based** FCPXML export.

**Not a one-click AI video editor:** Codex or an editor still has to review the footage and transcript and write the edit plan. Transcription, diagram generation and music sourcing are not built in. See [limitations](references/limitations.md).

## Requirements

- Python 3.10+
- FFmpeg and FFprobe on your PATH
- Codex with local file access

On macOS: `brew install ffmpeg`. See [setup](references/setup.md) for other systems and optional transcription.

## Install in Codex

Clone the repository, then copy the skill folder into `~/.agents/skills/pedagogical-video-editor/` (the install location may vary with your Codex configuration). Restart Codex and invoke `$pedagogical-video-editor`.

For example:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/pH-7/pedagogical-video-editor-skill.git ~/.agents/skills/pedagogical-video-editor
python3 ~/.agents/skills/pedagogical-video-editor/scripts/pve.py doctor
```

## First edit

Run these commands from the repository root and replace the source filename with your actual recording:

```bash
python3 scripts/pve.py init --project ./demo --source /path/to/recording.mp4 --language fr
python3 scripts/pve.py analyze --project ./demo
```

Optionally supply a UTF-8 `demo/transcript.srt` timed to the **original source recording**. Inspect the video and transcript, and edit `demo/edit_plan.json` to select cuts, zooms, graphics and sound cues. See the [plan schema](references/plan-schema.md) and [editorial guide](references/editorial-guide.md).

```bash
python3 scripts/pve.py render --project ./demo --preview
python3 scripts/pve.py qc --project ./demo --preview
python3 scripts/pve.py render --project ./demo
python3 scripts/pve.py qc --project ./demo
python3 scripts/pve.py export-fcpxml --project ./demo
```

The edited video is `demo/master.mp4`. A remapped `demo/edited_transcript.srt` is written when the original transcript exists. Review the full render, including speech cuts and caption synchronisation, before publishing. The FCPXML export contains source cuts, not fully editable recreations of all visual and audio treatments.

## Test

```bash
python3 scripts/test_pipeline.py
```

This creates synthetic footage in a temporary directory and tests the main rendering workflow. Passing this smoke test does **not** prove creative quality or compatibility with all input files.

## Safety and licensing

Only use footage, music, sound effects, fonts and illustrations you own or have permission to use. Keep original recordings backed up. Review reference videos for general editing principles without copying another creator's signature assets or identity.

**Licence:** no open-source licence has been selected yet. Public visibility alone does not grant permission to reuse, modify or redistribute this code. Add a `LICENSE` file after choosing the intended terms.
