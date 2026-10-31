#!/usr/bin/env python3
"""Small end-to-end smoke test using synthetic media."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def call(*args: str) -> None:
    subprocess.run(list(args), check=True)


def main() -> int:
    script = Path(__file__).with_name("pve.py")
    with tempfile.TemporaryDirectory(prefix="pve-test-") as tmp:
        root = Path(tmp)
        source = root / "source.mp4"
        project = root / "project"
        call(
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=4",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source),
        )
        call(sys.executable, str(script), "doctor")
        call(sys.executable, str(script), "init", "--project", str(project), "--source", str(source), "--language", "fr")
        call(sys.executable, str(script), "analyze", "--project", str(project))
        plan_path = project / "edit_plan.json"
        plan = json.loads(plan_path.read_text())
        plan["segments"] = [
            {"source_in": 0.0, "source_out": 1.8, "reason": "test cut 1"},
            {"source_in": 2.1, "source_out": 4.0, "reason": "test cut 2"},
        ]
        plan["zooms"] = [{"start": 0.5, "end": 1.4, "scale": 1.06, "x": 0.5, "y": 0.5, "reason": "test"}]
        filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], text=True, capture_output=True, check=True).stdout
        if " drawtext " in filters:
            plan["cards"] = [{"start": 2.0, "end": 3.2, "text": "Idée clé : tester", "position": "lower", "reason": "test French"}]
        # Source-time captions must be remapped when footage is cut.
        (project / "transcript.srt").write_text(
            "1\n00:00:00,500 --> 00:00:01,300\nBonjour\n\n"
            "2\n00:00:02,500 --> 00:00:03,500\nUne idée clé\n",
            encoding="utf-8",
        )
        plan["captions"]["burn_in"] = " subtitles " in filters
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        call(sys.executable, str(script), "render", "--project", str(project))
        retimed = project / "edited_transcript.srt"
        if not retimed.is_file():
            raise RuntimeError("Edited transcript was not generated")
        captions = retimed.read_text(encoding="utf-8")
        if "00:00:02,200 --> 00:00:03,200" not in captions:
            raise RuntimeError(f"Incorrect retimed caption: {captions}")
        if "00:00:00,500 --> 00:00:01,300" not in captions:
            raise RuntimeError(f"Incorrect first caption: {captions}")
        call(sys.executable, str(script), "render", "--project", str(project), "--preview")
        if not (project / "preview_manifest.json").is_file():
            raise RuntimeError("Preview manifest missing")
        call(sys.executable, str(script), "qc", "--project", str(project))
        call(sys.executable, str(script), "export-fcpxml", "--project", str(project))
        required = ["analysis.json", "master.mp4", "qc_report.json", "timeline.fcpxml", "render_manifest.json"]
        missing = [name for name in required if not (project / name).is_file()]
        if missing:
            raise RuntimeError(f"Missing outputs: {missing}")
        print("PASS: synthetic end-to-end pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
