# Setup and first project

## Required

- Codex with local file access
- Python 3.10 or later
- FFmpeg and FFprobe available on `PATH`

macOS with Homebrew: `brew install ffmpeg`

Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`

Windows with winget: `winget install Gyan.FFmpeg`

Run `python3 scripts/pve.py doctor` after installation.

Some minimal FFmpeg builds omit `drawtext` and `subtitles`. The doctor reports those optional capabilities. Core cutting, zoom, overlays, and audio can still work; install a full FFmpeg build with FreeType and libass for text cards and burned captions.

## Install the skill

Unzip the package. Copy the `pedagogical-video-editor` folder into the Codex skills directory, normally `~/.codex/skills/`, then restart Codex. Keep the folder name unchanged. Invoke it with `$pedagogical-video-editor` or ask Codex to edit an educational video.

## Supplying footage

Attach the source video to the Codex chat or place it in an accessible project folder, then give Codex the exact path. Large media is more reliable from a local path than as a chat attachment. Keep an untouched backup.

## Optional transcription

The pipeline accepts UTF-8 SRT at `<project>/transcript.srt`. If no transcript is supplied, install a transcription tool separately, for example Whisper, and export SRT. A typical local command is:

```bash
whisper input.mp4 --language French --output_format srt --output_dir project
```

Rename the result to `transcript.srt`. Model downloads, GPU support, speed, and accuracy depend on the local Whisper installation and are not provided by this skill. Review names, numbers, specialist vocabulary, and French elisions manually.

## Project outputs

- `project.json`: source and delivery settings
- `analysis.json`: technical and pause/scene observations
- `reference_style.json`: aggregate reference traits, when requested
- `edit_plan.json`: editable editorial decisions
- `transcript.srt`: editable captions
- `preview.mp4`: fast review render
- `master.mp4`: final render
- `qc_report.json`: automated checks
- `timeline.fcpxml`: cut-based editor interchange
- `render_manifest.json`: exact render inputs and command stages

Paths to source, music, visuals, and sound effects may be absolute. Move projects carefully or update those paths.
