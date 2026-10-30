# Limitations

- The included pipeline is deterministic and local. Semantic editorial decisions still require Codex or a human to inspect the transcript, footage, and previews.
- It does not bundle transcription, generative image/video models, stock libraries, licensed music, fonts, or cloud services.
- Silence and scene detection are heuristics. They can misread dramatic pauses, slides, low-motion footage, music, or noisy rooms.
- Automatic QC checks streams, duration, black/frozen spans, clipping indicators, and loudness where FFmpeg exposes them. It cannot prove factual accuracy, good taste, licensing, pedagogy, or perceptual quality.
- The FCPXML export represents source cuts. FFmpeg-rendered zooms, cards, overlays, captions, colour work, music, and sound effects may be flattened and must be rebuilt in an NLE for fully native editability.
- Reference analysis reports broad measurable traits. It cannot infer a complete creative system and must not be used to clone a living creator's distinctive style.
- Fonts and subtitle rendering vary by operating system and FFmpeg build. Test accented French text on the target machine.
- Rendering performance and supported codecs depend on the installed FFmpeg build and hardware. The pipeline defaults to broadly compatible H.264/AAC output.
- A preview is not approval. Review the full master before publishing or replacing source media.
