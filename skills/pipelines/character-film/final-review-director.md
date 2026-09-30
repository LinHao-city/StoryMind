# Film Final Review Director

Watch the actual rendered movie and inspect sampled opening, middle, climax,
and ending frames with `visual_qa`. Check identity, age impression, body,
wardrobe, physical state, locations, and action across cuts. Probe container,
duration, resolution, audio, and subtitles. Compare the runtime used against
the approved `film_proposal`; an unapproved swap is a critical failure.

Write `final_review` using the existing schema. A `revise` or `fail` verdict
blocks delivery; fix the relevant clip/edit/render and repeat review within
the approved budget. Present the movie to the user only after the report
passes and the user checkpoint is complete.
