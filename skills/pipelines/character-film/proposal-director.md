# Film Proposal Director

After character lock, review the approved story, target runtime, clip needs,
provider permissions, and project budget. Inspect
`video_compose.get_info()["render_engines"]`. When both Remotion and
HyperFrames are available, **present both** to the user with their benefits
and tradeoffs for this specific film; include `render_runtime='hyperframes'`
and FFmpeg when a straight cut is
appropriate. Recommend one, then wait for explicit approval before locking
`render_runtime`. Record the complete `render_runtime_selection` shortlist in
the decision log. Discuss composition mode separately: templated or atelier.
Set `renderer_family` to `cinematic-trailer` for this pipeline.

Present the video provider and model variant, estimated per-shot and total
cost, and whether its output URL may be public. For private family characters,
obtain explicit approval for that output-access risk or use an approved private
path. Store the choice and budget in `film_proposal`. Do not silently change
provider, model, or render runtime later. The production plan must be approved
before shot generation begins.
Use `film_provider_router` action `rank` to present the provider shortlist;
ranking never authorizes a call or swaps the approved provider.
