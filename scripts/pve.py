#!/usr/bin/env python3
"""Local, editable educational-video pipeline built on FFmpeg.

The script is intentionally dependency-free. Editorial intelligence lives in the
human/Codex-authored edit_plan.json; this module validates and renders it.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

VERSION = "1.0.0"


class PipelineError(RuntimeError):
    pass


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if check and result.returncode:
        tail = (result.stderr or result.stdout)[-5000:]
        raise PipelineError(f"Command failed ({result.returncode}): {' '.join(cmd[:8])}\n{tail}")
    return result


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot read valid JSON from {path}: {exc}") from exc


def resolve(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (project / path).resolve()


def probe(path: Path) -> dict[str, Any]:
    result = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ])
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise PipelineError(f"No video stream in {path}")
    return {
        "path": str(path.resolve()),
        "duration": float(fmt.get("duration") or video.get("duration") or 0),
        "size_bytes": int(fmt.get("size") or path.stat().st_size),
        "format_name": fmt.get("format_name"),
        "video": {
            "codec": video.get("codec_name"),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "fps": fraction(video.get("avg_frame_rate", "0/1")),
            "pix_fmt": video.get("pix_fmt"),
        },
        "audio": None if not audio else {
            "codec": audio.get("codec_name"),
            "sample_rate": int(audio.get("sample_rate") or 0),
            "channels": int(audio.get("channels") or 0),
        },
    }


def fraction(value: str) -> float:
    try:
        a, b = value.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def ffmpeg_filters() -> set[str]:
    result = run(["ffmpeg", "-hide_banner", "-filters"], check=False)
    return set(re.findall(r"^\s*[.A-Z|]{2,3}\s+([a-zA-Z0-9_]+)\s", result.stdout, re.MULTILINE))


def project_config(project: Path) -> dict[str, Any]:
    config = read_json(project / "project.json")
    config["source"] = str(resolve(project, config["source"]))
    if not Path(config["source"]).is_file():
        raise PipelineError(f"Source not found: {config['source']}")
    return config


def cmd_doctor(_: argparse.Namespace) -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    filters = ffmpeg_filters() if not missing else set()
    report = {
        "pipeline_version": VERSION,
        "python": sys.version.split()[0],
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "status": "fail" if missing else "pass",
        "missing": missing,
        "features": {
            "core_editing": all(name in filters for name in ("overlay", "zoompan", "loudnorm")),
            "text_cards": "drawtext" in filters,
            "burned_captions": "subtitles" in filters,
        },
        "note": "Text cards and burned captions need an FFmpeg build with drawtext/libass. Editable SRT remains available without them.",
    }
    print(json.dumps(report, indent=2))
    if missing:
        raise PipelineError("Install FFmpeg/FFprobe and run doctor again")


def cmd_init(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise PipelineError(f"Source not found: {source}")
    project.mkdir(parents=True, exist_ok=True)
    info = probe(source)
    width = args.width or info["video"]["width"]
    height = args.height or info["video"]["height"]
    fps = args.fps or round(info["video"]["fps"] or 30, 3)
    config = {
        "version": 1,
        "source": str(source),
        "language": args.language,
        "audience": args.audience,
        "output": {"width": width, "height": height, "fps": fps},
    }
    write_json(project / "project.json", config)
    plan = {
        "version": 1,
        "output": config["output"],
        "segments": [{"source_in": 0.0, "source_out": round(info["duration"], 3), "reason": "conservative full-source starter"}],
        "zooms": [], "cards": [], "visuals": [], "sound_effects": [],
        "music": None,
        "captions": {"path": "transcript.srt", "burn_in": False},
        "notes": ["Starter plan only: inspect the transcript and footage before editing."],
    }
    write_json(project / "edit_plan.json", plan)
    print(f"Created editable project at {project}")


def detect_silence(source: Path) -> list[dict[str, float]]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(source),
        "-af", "silencedetect=noise=-35dB:d=0.45", "-f", "null", "-",
    ], check=False)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", result.stderr)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)", result.stderr)]
    return [
        {"start": round(start, 3), "end": round(end, 3), "duration": round(duration, 3)}
        for start, (end, duration) in zip(starts, ends)
    ]


def detect_scenes(source: Path) -> list[float]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(source),
        "-vf", "select='gt(scene,0.32)',showinfo", "-an", "-f", "null", "-",
    ], check=False)
    return [round(float(x), 3) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr)]


def loudness(source: Path) -> dict[str, float | None]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(source),
        "-af", "ebur128=peak=true", "-f", "null", "-",
    ], check=False)
    values = re.findall(r"I:\s*(-?[0-9.]+) LUFS", result.stderr)
    peaks = re.findall(r"Peak:\s*(-?[0-9.]+) dBFS", result.stderr)
    return {
        "integrated_lufs": float(values[-1]) if values else None,
        "true_peak_dbfs": float(peaks[-1]) if peaks else None,
    }


def analyse_file(source: Path) -> dict[str, Any]:
    info = probe(source)
    silences = detect_silence(source) if info["audio"] else []
    scenes = detect_scenes(source)
    silence_total = sum(s["duration"] for s in silences)
    return {
        "technical": info,
        "silence": {
            "threshold_db": -35,
            "minimum_duration": 0.45,
            "spans": silences,
            "total_seconds": round(silence_total, 3),
            "ratio": round(silence_total / info["duration"], 4) if info["duration"] else 0,
        },
        "scenes": {
            "threshold": 0.32,
            "timestamps": scenes,
            "count": len(scenes),
            "average_interval": round(info["duration"] / max(1, len(scenes) + 1), 3),
        },
        "loudness": loudness(source) if info["audio"] else {},
        "interpretation_warning": "Heuristic measurements require editorial review.",
    }


def cmd_analyze(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    source = Path(project_config(project)["source"])
    report = analyse_file(source)
    write_json(project / "analysis.json", report)
    print(f"Wrote {project / 'analysis.json'}")


def cmd_reference(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    project_config(project)
    files = [Path(v).expanduser().resolve() for v in args.videos]
    for file in files:
        if not file.is_file():
            raise PipelineError(f"Reference not found: {file}")
    reports = [analyse_file(file) for file in files]
    intervals = [r["scenes"]["average_interval"] for r in reports]
    pauses = [r["silence"]["ratio"] for r in reports]
    style = {
        "references": reports,
        "aggregate": {
            "reference_count": len(reports),
            "scene_interval_range_seconds": [min(intervals), max(intervals)],
            "silence_ratio_range": [min(pauses), max(pauses)],
        },
        "usage": "Use as broad evidence about pacing. Do not clone identity, wording, graphics, or music.",
    }
    write_json(project / "reference_style.json", style)
    print(f"Wrote {project / 'reference_style.json'}")


def validate_plan(project: Path, plan: dict[str, Any], source_info: dict[str, Any]) -> float:
    if plan.get("version") != 1:
        raise PipelineError("Unsupported edit plan version")
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise PipelineError("Plan needs at least one segment")
    output = plan.get("output", {})
    if not all(isinstance(output.get(k), (int, float)) and output[k] > 0 for k in ("width", "height", "fps")):
        raise PipelineError("Output width, height, and fps must be positive numbers")
    if int(output["width"]) % 2 or int(output["height"]) % 2:
        raise PipelineError("Output width and height must be even for H.264 yuv420p")
    previous = -1.0
    total = 0.0
    for i, seg in enumerate(segments):
        start = float(seg["source_in"])
        end = float(seg["source_out"])
        if start < 0 or end <= start or end > source_info["duration"] + 0.05 or start < previous:
            raise PipelineError(f"Invalid or overlapping segment {i}: {seg}")
        previous = end
        total += end - start
    for group in ("zooms", "cards", "visuals", "sound_effects"):
        if not isinstance(plan.get(group, []), list):
            raise PipelineError(f"{group} must be a list")
        for event in plan.get(group, []):
            start = float(event.get("start", -1))
            end = float(event.get("end", start))
            if start < 0 or start > total or end < start or end > total + 0.05:
                raise PipelineError(f"Invalid {group} timing: {event}")
    for zoom in plan.get("zooms", []):
        if not 1.0 <= float(zoom["scale"]) <= 1.5:
            raise PipelineError(f"Zoom scale outside safe renderer range: {zoom}")
    for group in ("visuals", "sound_effects"):
        for event in plan.get(group, []):
            path = resolve(project, event["path"])
            if not path.is_file():
                raise PipelineError(f"Missing {group} asset: {path}")
    music = plan.get("music")
    if music and not resolve(project, music["path"]).is_file():
        raise PipelineError(f"Missing music: {resolve(project, music['path'])}")
    captions = plan.get("captions") or {}
    if captions.get("burn_in") and not resolve(project, captions["path"]).is_file():
        raise PipelineError(f"Missing captions: {resolve(project, captions['path'])}")
    return total


def ffmpeg_filter_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def locate_font() -> str | None:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    return next((p for p in candidates if Path(p).is_file()), None)


def zoom_expression(events: list[dict[str, Any]], fps: float) -> str:
    expr = "1"
    for event in reversed(events):
        start = round(float(event["start"]) * fps)
        end = round(float(event["end"]) * fps)
        scale = float(event["scale"])
        expr = f"if(between(on\\,{start}\\,{end})\\,{scale:.5f}\\,{expr})"
    return expr


def create_cut_mezzanine(source: Path, plan: dict[str, Any], out: Path, width: int, height: int, fps: float) -> list[str]:
    filters: list[str] = []
    inputs: list[str] = []
    for i, seg in enumerate(plan["segments"]):
        start, end = float(seg["source_in"]), float(seg["source_out"])
        filters.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{i}]"
        )
        filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]")
        inputs.extend([f"[v{i}]", f"[a{i}]"])
    filters.append("".join(inputs) + f"concat=n={len(plan['segments'])}:v=1:a=1[v][a]")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-i", str(source),
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
        "-c:a", "pcm_s16le", str(out),
    ]
    run(cmd)
    return cmd


def create_presentation(project: Path, base: Path, plan: dict[str, Any], out: Path, duration: float, preview: bool) -> list[str]:
    output = plan["output"]
    factor = 0.5 if preview else 1.0
    width = max(2, int(output["width"] * factor) // 2 * 2)
    height = max(2, int(output["height"] * factor) // 2 * 2)
    fps = float(output["fps"])
    available_filters = ffmpeg_filters()
    if plan.get("cards") and "drawtext" not in available_filters:
        raise PipelineError("This FFmpeg build lacks drawtext. Install a full FFmpeg build, or replace cards with PNG visual overlays.")
    captions = plan.get("captions") or {}
    if captions.get("burn_in") and "subtitles" not in available_filters:
        raise PipelineError("This FFmpeg build lacks the subtitles/libass filter. Install a full build or deliver the editable SRT separately.")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(base)]
    visuals = plan.get("visuals", [])
    input_index: dict[tuple[str, int], int] = {}
    index = 1
    for i, visual in enumerate(visuals):
        cmd += ["-loop", "1", "-i", str(resolve(project, visual["path"]))]
        input_index[("visual", i)] = index
        index += 1
    music = plan.get("music")
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(resolve(project, music["path"]))]
        input_index[("music", 0)] = index
        index += 1
    for i, effect in enumerate(plan.get("sound_effects", [])):
        cmd += ["-i", str(resolve(project, effect["path"]))]
        input_index[("sfx", i)] = index
        index += 1

    filters: list[str] = []
    current = "v0"
    zooms = plan.get("zooms", [])
    if zooms:
        z = zoom_expression(zooms, fps)
        filters.append(
            f"[0:v]zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}[{current}]"
        )
    else:
        filters.append(f"[0:v]scale={width}:{height},setsar=1[{current}]")

    for i, visual in enumerate(visuals):
        event = visual
        fraction_width = min(0.9, max(0.1, float(event.get("width_fraction", 0.38))))
        vw = int(width * fraction_width) // 2 * 2
        filters.append(f"[{input_index[('visual', i)]}:v]scale={vw}:-2[img{i}]")
        position = event.get("position", "right")
        x = "W-w-48" if position == "right" else ("48" if position == "left" else "(W-w)/2")
        y = "(H-h)/2"
        nxt = f"v{i + 1}"
        filters.append(
            f"[{current}][img{i}]overlay=x={x}:y={y}:"
            f"enable='between(t,{float(event['start'])},{float(event['end'])})':eof_action=pass[{nxt}]"
        )
        current = nxt

    font = locate_font()
    for i, card in enumerate(plan.get("cards", [])):
        if not font:
            raise PipelineError("No supported font found for card rendering")
        card_file = project / f".pve-card-{i}.txt"
        card_file.write_text(str(card["text"]), encoding="utf-8")
        enable = f"between(t,{float(card['start'])},{float(card['end'])})"
        position = card.get("position", "lower")
        y = "h*0.76" if position == "lower" else ("h*0.14" if position == "upper" else "(h-text_h)/2")
        nxt = f"card{i}"
        filters.append(
            f"[{current}]drawbox=x=w*0.08:y={y}-24:w=w*0.84:h=96:color=black@0.68:t=fill:enable='{enable}',"
            f"drawtext=fontfile='{ffmpeg_filter_path(Path(font))}':textfile='{ffmpeg_filter_path(card_file)}':"
            f"fontcolor=white:fontsize={max(24, int(height * 0.038))}:x=(w-text_w)/2:y={y}:enable='{enable}'[{nxt}]"
        )
        current = nxt

    if captions.get("burn_in"):
        cap = resolve(project, captions["path"])
        nxt = "captioned"
        filters.append(
            f"[{current}]subtitles='{ffmpeg_filter_path(cap)}':"
            f"force_style='FontSize=18,Outline=2,Shadow=0,MarginV=42,Alignment=2'[{nxt}]"
        )
        current = nxt

    audio_tracks = ["[0:a]"]
    if music:
        idx = input_index[("music", 0)]
        start = max(0.0, float(music.get("start", 0)))
        end = min(duration, float(music.get("end", duration)))
        delay = round(start * 1000)
        gain = float(music.get("gain_db", -28))
        filters.append(f"[{idx}:a]atrim=0:{max(0.01, end-start)},asetpts=PTS-STARTPTS,volume={gain}dB,adelay={delay}|{delay}[music]")
        audio_tracks.append("[music]")
    for i, effect in enumerate(plan.get("sound_effects", [])):
        idx = input_index[("sfx", i)]
        delay = round(float(effect["start"]) * 1000)
        gain = float(effect.get("gain_db", -18))
        filters.append(f"[{idx}:a]volume={gain}dB,adelay={delay}|{delay}[sfx{i}]")
        audio_tracks.append(f"[sfx{i}]")
    if len(audio_tracks) > 1:
        filters.append("".join(audio_tracks) + f"amix=inputs={len(audio_tracks)}:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        audio_map = "[aout]"
    else:
        filters.append("[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        audio_map = "[aout]"

    cmd += [
        "-filter_complex", ";".join(filters), "-map", f"[{current}]", "-map", audio_map,
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
        "-crf", "25" if preview else "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k" if preview else "256k", "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    for file in project.glob(".pve-card-*.txt"):
        file.unlink(missing_ok=True)
    return cmd



def retime_srt(source: Path, destination: Path, segments: list[dict[str, Any]]) -> int:
    """Map source-time SRT cues to the cut timeline, clipping cues at edit boundaries."""
    raw = source.read_text(encoding="utf-8-sig").replace("\\r\\n", "\\n")
    blocks = re.split(r"\\n\\s*\\n", raw.strip()) if raw.strip() else []
    stamp = re.compile(r"^(\\d{2}):(\\d{2}):(\\d{2})[,\\.](\\d{3})$")
    timing = re.compile(r"^(.+?)\\s+-->\\s+(.+?)(?:\\s+.*)?$")
    def parse(value: str) -> float:
        found = stamp.fullmatch(value.strip())
        if not found:
            raise PipelineError(f"Unsupported SRT timestamp: {value}")
        h, m, sec, ms = map(int, found.groups())
        return h * 3600 + m * 60 + sec + ms / 1000
    def format_time(value: float) -> str:
        ms = max(0, round(value * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        sec, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    output: list[str] = []
    cumulative: list[tuple[float, float, float]] = []
    offset = 0.0
    for segment in segments:
        a, b = float(segment["source_in"]), float(segment["source_out"])
        cumulative.append((a, b, offset))
        offset += b - a
    for block in blocks:
        lines = block.splitlines()
        index = 1 if lines and lines[0].strip().isdigit() else 0
        if len(lines) <= index:
            raise PipelineError("Invalid SRT cue with no timestamp")
        match = timing.fullmatch(lines[index].strip())
        if not match:
            raise PipelineError(f"Invalid SRT cue: {lines[index]}")
        a, b = parse(match.group(1)), parse(match.group(2))
        if b <= a:
            raise PipelineError("SRT cue end must follow start")
        text = "\\n".join(lines[index + 1:])
        if not text.strip():
            continue
        for seg_a, seg_b, start in cumulative:
            lo, hi = max(a, seg_a), min(b, seg_b)
            if hi - lo < 0.02:
                continue
            cue_a, cue_b = start + lo - seg_a, start + hi - seg_a
            output.append(f"{len(output)+1}\\n{format_time(cue_a)} --> {format_time(cue_b)}\\n{text}")
    destination.write_text("\\n\\n".join(output) + ("\\n" if output else ""), encoding="utf-8")
    return len(output)


def cmd_render(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    config = project_config(project)
    source = Path(config["source"])
    source_info = probe(source)
    if not source_info["audio"]:
        raise PipelineError("Renderer currently requires a source audio stream")
    plan = read_json(project / "edit_plan.json")
    duration = validate_plan(project, plan, source_info)
    output = plan["output"]
    width, height, fps = int(output["width"]), int(output["height"]), float(output["fps"])
    out = project / ("preview.mp4" if args.preview else "master.mp4")
    # Captions in a source transcript do not match the edited timeline after cuts.
    render_plan = dict(plan)
    captions = plan.get("captions") or {}
    if captions.get("path") and resolve(project, captions["path"]).is_file():
        edited_srt = project / "edited_transcript.srt"
        retime_srt(resolve(project, captions["path"]), edited_srt, plan["segments"])
        render_plan["captions"] = dict(captions, path=str(edited_srt))
    with tempfile.TemporaryDirectory(prefix="pve-") as tmp:
        base = Path(tmp) / "cut.mov"
        cut_cmd = create_cut_mezzanine(source, plan, base, width, height, fps)
        finish_cmd = create_presentation(project, base, render_plan, out, duration, args.preview)
    manifest = {
        "pipeline_version": VERSION,
        "source": str(source),
        "plan": str(project / "edit_plan.json"),
        "output": str(out),
        "preview": args.preview,
        "duration": duration,
        "stages": [cut_cmd, finish_cmd],
    }
    write_json(project / ("preview_manifest.json" if args.preview else "render_manifest.json"), manifest)
    print(f"Rendered {out}")


def diagnostic_spans(path: Path, filter_name: str, pattern: str) -> list[float]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-vf", filter_name, "-an", "-f", "null", "-",
    ], check=False)
    return [float(x) for x in re.findall(pattern, result.stderr)]


def cmd_qc(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    target = project / ("preview.mp4" if args.preview else "master.mp4")
    if not target.is_file():
        raise PipelineError(f"Render not found: {target}")
    info = probe(target)
    plan = read_json(project / "edit_plan.json")
    expected = sum(float(s["source_out"]) - float(s["source_in"]) for s in plan["segments"])
    black = diagnostic_spans(target, "blackdetect=d=1.5:pix_th=0.02", r"black_duration:([0-9.]+)")
    freezes = diagnostic_spans(target, "freezedetect=n=-55dB:d=3", r"freeze_duration: ([0-9.]+)")
    levels = loudness(target)
    checks = {
        "has_video": bool(info["video"]),
        "has_audio": bool(info["audio"]),
        "duration_matches": abs(info["duration"] - expected) < max(0.25, expected * 0.005),
        "dimensions_match": info["video"]["width"] == int(plan["output"]["width"]) and info["video"]["height"] == int(plan["output"]["height"]),
        "no_long_black_spans": not black,
        "loudness_in_review_range": levels.get("integrated_lufs") is not None and -19 <= float(levels["integrated_lufs"]) <= -13,
        "true_peak_safe": levels.get("true_peak_dbfs") is not None and float(levels["true_peak_dbfs"]) <= -1.0,
    }
    if args.preview:
        checks.pop("dimensions_match")
    report = {
        "target": str(target), "technical": info, "expected_duration": expected,
        "black_spans_seconds": black, "freeze_spans_seconds": freezes,
        "loudness": levels, "checks": checks,
        "status": "pass" if all(checks.values()) else "review",
        "manual_review_required": [
            "Watch the complete render for clipped speech, awkward cuts, factual accuracy, caption errors, asset rights, and pedagogical clarity.",
            "Investigate freeze spans: they may be intentional slides or a real fault.",
        ],
    }
    write_json(project / "qc_report.json", report)
    print(json.dumps({"report": str(project / "qc_report.json"), "status": report["status"], "checks": checks}, indent=2))


def seconds_fraction(value: float, fps: float) -> str:
    frames = round(value * fps)
    return f"{frames}/{round(fps)}s"


def cmd_fcpxml(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    config = project_config(project)
    source = Path(config["source"])
    info = probe(source)
    plan = read_json(project / "edit_plan.json")
    validate_plan(project, plan, info)
    fps = float(plan["output"]["fps"])
    frame_duration = f"1/{round(fps)}s"
    width, height = int(plan["output"]["width"]), int(plan["output"]["height"])
    clips = []
    offset = 0.0
    for i, seg in enumerate(plan["segments"], 1):
        start = float(seg["source_in"])
        duration = float(seg["source_out"]) - start
        clips.append(
            f'<asset-clip name="Cut {i}" ref="r2" offset="{seconds_fraction(offset, fps)}" '
            f'start="{seconds_fraction(start, fps)}" duration="{seconds_fraction(duration, fps)}"/>'
        )
        offset += duration
    source_uri = source.as_uri()
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
  <resources>
    <format id="r1" name="FFVideoFormat{height}p{round(fps)}" frameDuration="{frame_duration}" width="{width}" height="{height}"/>
    <asset id="r2" name="{xml_escape(source.name)}" src="{xml_escape(source_uri)}" start="0s" duration="{seconds_fraction(info['duration'], fps)}" hasVideo="1" hasAudio="1" format="r1"/>
  </resources>
  <library><event name="Pedagogical Edit"><project name="Pedagogical Edit"><sequence format="r1" duration="{seconds_fraction(offset, fps)}"><spine>
    {''.join(clips)}
  </spine></sequence></project></event></library>
</fcpxml>
'''
    path = project / "timeline.fcpxml"
    path.write_text(xml, encoding="utf-8")
    print(f"Wrote {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pedagogical Video Editor pipeline")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Check local dependencies")
    doctor.set_defaults(func=cmd_doctor)
    init = sub.add_parser("init", help="Create an editable project")
    init.add_argument("--project", required=True)
    init.add_argument("--source", required=True)
    init.add_argument("--language", default="fr")
    init.add_argument("--audience", default="general")
    init.add_argument("--width", type=int)
    init.add_argument("--height", type=int)
    init.add_argument("--fps", type=float)
    init.set_defaults(func=cmd_init)
    for name, function in (("analyze", cmd_analyze), ("render", cmd_render), ("qc", cmd_qc), ("export-fcpxml", cmd_fcpxml)):
        item = sub.add_parser(name)
        item.add_argument("--project", required=True)
        if name in ("render", "qc"):
            item.add_argument("--preview", action="store_true")
        item.set_defaults(func=function)
    reference = sub.add_parser("reference", help="Measure authorised reference videos")
    reference.add_argument("--project", required=True)
    reference.add_argument("--videos", nargs="+", required=True)
    reference.set_defaults(func=cmd_reference)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
