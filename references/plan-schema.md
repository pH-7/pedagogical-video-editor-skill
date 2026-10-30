# Edit plan schema

Times are seconds on the original source for `segments`, and seconds on the edited timeline for presentation events.

```json
{
  "version": 1,
  "output": {"width": 1920, "height": 1080, "fps": 30},
  "segments": [{"source_in": 0.0, "source_out": 12.4, "reason": "opening"}],
  "zooms": [{"start": 4.0, "end": 7.0, "scale": 1.06, "x": 0.5, "y": 0.42, "reason": "key claim"}],
  "cards": [{"start": 8.0, "end": 11.0, "text": "Une idée = une décision", "position": "lower", "reason": "definition"}],
  "visuals": [{"start": 12.0, "end": 18.0, "path": "diagram.png", "position": "right", "width_fraction": 0.38, "reason": "show process"}],
  "sound_effects": [{"start": 12.0, "path": "soft-whoosh.wav", "gain_db": -18.0, "reason": "diagram arrival"}],
  "music": {"path": "music.wav", "gain_db": -28.0, "start": 0.0, "end": 45.0},
  "captions": {"path": "transcript.srt", "burn_in": true},
  "notes": []
}
```

`segments` must be ordered, non-overlapping, positive-duration ranges inside the source. Empty segments are invalid. Positions are `left`, `right`, `centre`, `upper`, or `lower` as appropriate. Coordinates `x` and `y` are normalised focal points from 0 to 1.

The renderer accepts PNG/JPEG still visuals. Use transparent PNG for diagrams and labels. It uses the installed font for cards and the FFmpeg subtitle renderer for burn-in captions. Keep paths relative to the project where possible.

The generated starter plan retains the full source and proposes restrained zooms only. Codex should change it after semantic review; do not call the starter plan an intelligent final edit.
