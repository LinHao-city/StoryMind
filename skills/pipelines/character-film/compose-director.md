# Film Compose Director

Read the approved `film_proposal`, `edit_decisions`, and `asset_manifest`.
Verify the runtime and composition mode have not changed. Call `video_compose`
with that exact render_runtime and project-local output path. HyperFrames and
Remotion remain valid when approved; FFmpeg is suitable for video-led straight
cuts. Do not silently substitute a still-image animatic for motion clips.

Probe the produced MP4 with `visual_qa` and record its real path, codec,
resolution, duration, and warnings in `render_report`. If the runtime is
unavailable, surface the blocker and ask before selecting another one.
