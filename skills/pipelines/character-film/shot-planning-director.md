# Shot Planning Director

Read the locked story and character bible. Use StoryboardPlanner when available
for cinematic suggestions, but the canonical output is `film_shot_plan`.
Every shot must identify its scene, location, duration, camera, lighting,
characters, locked outfit IDs, state, position, and video prompt. The shot
durations must sum to the approved runtime. Record changes of physical or
wardrobe state explicitly; do not let continuity drift between shots.

Present the shot plan for user approval before keyframe generation. Keep
character master, full-body, outfit, and privacy references attached by ID.
Do not put original family source photos in shot prompts or reference sets.
