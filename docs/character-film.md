# Character Film pipeline

`character-film` is a beta, character-first pipeline for a short fictional movie.
It reuses StoryMind checkpoints, review, cost tracking, provider tools, and
composition. The existing `cinematic` pipeline is unchanged. A run moves through:

`story_development` → `character_discovery` → `character_distillation` →
`character_lock` → `proposal` → `shot_planning` → `keyframe_generation` →
`video_generation` → `edit` → `compose` → `final_review`.

Read `pipeline_defs/character-film.yaml` and each stage director skill before
production. Run the registry preflight in `AGENT_GUIDE.md`; present the provider
menu, costs, and both available composition runtimes. Review and checkpoint
every stage. The story, character selections, locks, proposal, and final review
require explicit user approval. A completed checkpoint carries fingerprints of
its upstream artifacts. Revisions to a story, cast, shot plan, references, or
media make dependent checkpoints stale on resume.

## First production target

Start with a 10–20 second film, one character, and a small number of shots.
Develop and lock the story before making any images. If the character comes
from personal photographs, take in 2–3 photos locally and record source
classification and permissions. A local-only source remains local. Remote
character creation from a source photo requires separate, named provider
approval. Creating an AI-derived reference never implies permission to upload
the original photo again.

The host's image generation is an **agent-native** capability. It is invoked
by the agent, not impersonated as a Python `BaseTool`. Save its output under
`projects/<project-id>/`, then call `character_media` to register the file,
hash, provider, model, and prompt. Source photos go through `intake_source`.
The existing image providers remain optional paths and require a clear user
decision for private content.

Generate three fictionalized candidates for the first character. Present them
to the user and record the selected candidate. Build a derived master, full
body reference, and every story-required outfit. The lock gate verifies that
all references exist, decode as images, match their approved hashes, and do
not reuse original source-photo bytes. Identity and wardrobe remain separate.

## Shot and clip contracts

The shot plan links each shot to an approved scene, location, character, outfit,
and declared state. Shot durations add up to the locked story's target runtime.
Keyframes use only derived references; each has a Continuity Supervisor review
and a separate Creative Director review. Both must pass before video generation.

For a video shot, use `film_provider_router` to rank eligible providers and
inspect a `plan` before `generate`. The plan requires the locked story, locked
cast, shot plan, keyframes, shot ID, named provider/model, and explicit provider
policy. The policy records `approved_provider`, `approved_by: user`,
`model_variant`, `max_call_cost_usd`, and `budget_usd`. For private characters,
it also needs `public_output_approval` with `approved_by: user` and the named
provider. The `film_proposal` must carry this exact policy, and the router
checks it again before any upload. This is necessary because a provider output URL may be accessible to
others. Do not upload private material until the user has accepted that output
handling. Do not switch providers or model variants silently.

The router maps the approved keyframe and derived character references into
Kling v3 Elements or Seedance reference images. It never selects a provider
automatically for `generate`; the user's approved choice is required. Every
clip is probed as MP4, sampled for visual review, and checked for a continuity
and creative pass. `lib.film_retry.next_take_action` keeps policy rejection,
technical failure, quality retry, budget failure, and human escalation distinct.
Policy rejection is never a cue to alter a minor's age or probe moderation.

An `edit_decisions` artifact and `asset_manifest` include only approved clips
in shot order. `video_compose` uses the proposal's approved runtime and
composition mode. The render and final review gates probe the project-local
movie and require a four-frame visual spot check plus explicit character and
wardrobe continuity results. Creative judgment remains with the reviewers;
the Python gates enforce artifact and media integrity.

## Experiments and release gate

Run the brief's experiments in order with actual approved inputs:

1. **A:** Distill one character from 2–3 photos or descriptions; present three
   candidates and build a derived master pack after the user selects one.
2. **B:** Generate the locked character in five distinct static scenes; review
   identity, body, and wardrobe drift.
3. **C:** Generate short Kling takes using only derived references; sample and
   review each clip.
4. **D:** Generate three consecutive shots and verify cross-shot continuity.
5. **E:** Assemble and review a 10–20 second movie.

The pipeline implementation and synthetic FFmpeg test do not prove that a real
character remains recognizable across generated shots. Record actual results
for A–E before calling the V1 promise validated. Phase 7 work such as a UI,
training, voices, or longer films begins only after a successful real movie.

### Local three-shot trial

A private 12-second trial used three separately generated four-second shots,
then an FFmpeg straight-cut render. Opening, middle, and closing frames from
each clip (nine total) and six frames from the final render were inspected.
The two principal characters remained recognizable across both cuts, with
their main outfits and one toy intact. The final MP4 passed container, duration,
resolution, and audio-stream checks. Minor differences remained in a shoe
color and one camera angle. The video calls cost $1.512 in total.

This is evidence for experiments C, D, and E on one local scenario. Experiment
B's five-scene static identity test and broader repeated trials remain open;
the pipeline stays beta. Private source media and the trial outputs are kept in
ignored local project workspaces and are not part of this repository.
