# Film Edit Director

Read only the continuity-approved clips. Build `asset_manifest` with absolute
paths to their project-local files for `video_compose` resolution, and
`edit_decisions` in the approved shot order. Carry the
exact `render_runtime` and composition mode from `film_proposal`. Trim for
pacing only within the available clip duration; do not drop an approved story
beat without user approval. Keep source family photos out of the edit.
