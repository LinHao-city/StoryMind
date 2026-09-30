"""Phase 1 character-film gates and checkpoint freshness."""

from __future__ import annotations

import copy
import hashlib

import pytest
from PIL import Image

from lib.character_film_state import FilmStateError, lock_character, lock_story, revise_story, story_fingerprint
from lib.character_film_state import artifact_fingerprint
from lib.checkpoint import CheckpointValidationError, get_completed_stages, get_next_stage, write_checkpoint
from lib.pipeline_loader import load_pipeline
from tools.planning.character_manager import CharacterManager


def story(status="AWAITING_APPROVAL"):
    return {
        "version": "1.0", "revision": 1, "title": "The Lighthouse",
        "premise": "A child finds a message.", "synopsis": "A child solves a mystery.",
        "narrative": {"beginning": "A message arrives.", "escalation": "The clues conflict.",
                      "climax": "The child opens the box.", "resolution": "The family reunites."},
        "genre": "adventure", "tone": "warm", "target_duration_seconds": 180,
        "characters": ["protagonist"], "locations": ["harbor"],
        "scenes": [{"id": "opening", "location": "harbor"}], "status": status,
    }


def bible(approved_story):
    character = CharacterManager.draft("protagonist", "lead", "minor", "private_family_photo")
    character["required_outfits"] = ["raincoat"]
    return {"version": "1.0", "story_fingerprint": story_fingerprint(approved_story), "characters": [character]}


def test_manifest_and_skills_are_loadable():
    manifest = load_pipeline("character-film")
    assert [stage["name"] for stage in manifest["stages"]] == [
        "story_development", "character_discovery", "character_distillation",
        "character_lock", "proposal", "shot_planning", "keyframe_generation",
        "video_generation", "edit", "compose", "final_review",
    ]


def test_story_requires_user_approval_and_revision_clears_lock():
    with pytest.raises(FilmStateError):
        lock_story(story(), "agent")
    approved = lock_story(story(), "user")
    revised = revise_story(approved, {"premise": "A new message appears."})
    assert revised["status"] == "DRAFT"
    assert revised["revision"] == 2
    assert "approval" not in revised
    assert story_fingerprint(revised) != story_fingerprint(approved)


def test_checkpoint_gates_lock_and_upstream_freshness(tmp_path):
    pipeline_dir = tmp_path / "pipelines"
    project_dir = tmp_path / "projects" / "film-1"
    approved_story = lock_story(story(), "user")
    cast = bible(approved_story)

    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "story_development"
    with pytest.raises(CheckpointValidationError):
        write_checkpoint(pipeline_dir, "film-1", "character_discovery", "completed",
                         {"character_bible": cast}, pipeline_type="character-film")
    with pytest.raises(CheckpointValidationError):
        write_checkpoint(pipeline_dir, "film-1", "story_development", "completed",
                         {"story_bible": story()}, pipeline_type="character-film")

    write_checkpoint(pipeline_dir, "film-1", "story_development", "completed",
                     {"story_bible": approved_story}, pipeline_type="character-film")
    write_checkpoint(pipeline_dir, "film-1", "character_discovery", "completed",
                     {"character_bible": cast}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "character_distillation"

    candidate_dir = project_dir / "characters" / "protagonist" / "candidate"
    candidate_dir.mkdir(parents=True)
    candidate_path = candidate_dir / "candidate-1.png"
    Image.new("RGB", (16, 16), "blue").save(candidate_path)
    candidate_asset = {
        "path": "characters/protagonist/candidate/candidate-1.png",
        "sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "origin": "generated", "provider": "fixture", "model": "fixture",
        "prompt": "test candidate",
    }
    candidates = {
        "version": "1.0", "story_fingerprint": story_fingerprint(approved_story),
        "selections": [{
            "character_id": "protagonist", "trait_profile": "Child with dark hair",
            "fictionalization_level": 3,
            "candidates": [{"id": "candidate-1", "asset": candidate_asset}],
            "selected_candidate_id": "candidate-1",
            "approval": {"approved_by": "user", "approved_at": "2026-09-29T00:00:00Z"},
        }],
    }
    write_checkpoint(pipeline_dir, "film-1", "character_distillation", "completed",
                     {"character_candidates": candidates}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "character_lock"

    with pytest.raises(CheckpointValidationError):
        write_checkpoint(pipeline_dir, "film-1", "character_lock", "completed",
                         {"character_bible": cast}, pipeline_type="character-film")

    refs = project_dir / "characters" / "protagonist"
    refs.mkdir(parents=True, exist_ok=True)
    for filename in ("master.png", "full-body.png", "raincoat.png"):
        Image.new("RGB", (16, 16), "blue").save(refs / filename)
    ready = copy.deepcopy(cast)
    person = ready["characters"][0]
    person["selected_candidate_id"] = "candidate-1"
    person["identity"] = {
        "master": "characters/protagonist/master.png",
        "full_body": "characters/protagonist/full-body.png",
    }
    person["outfits"] = {"raincoat": {
        "reference": "characters/protagonist/raincoat.png", "locked": True,
    }}
    person["status"] = "AWAITING_APPROVAL"
    ready["characters"][0] = lock_character(person, project_dir, "user")
    write_checkpoint(pipeline_dir, "film-1", "character_lock", "completed",
                     {"character_bible": ready}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "proposal"
    proposal = {"version": "1.0", "story_fingerprint": story_fingerprint(approved_story),
                "renderer_family": "cinematic-trailer",
                "render_runtime": "ffmpeg", "composition_mode": "templated",
                "options_considered": ["ffmpeg", "remotion", "hyperframes"],
                "approved_by": "user", "approved_at": "2026-09-29T00:00:00Z",
                "budget_usd": 10.0}
    write_checkpoint(pipeline_dir, "film-1", "proposal", "completed",
                     {"film_proposal": proposal}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "shot_planning"
    plan = {"version": "1.0", "story_fingerprint": story_fingerprint(approved_story),
            "shots": [{"id": "shot-1", "scene_id": "opening", "duration_seconds": 180,
                       "location": "harbor", "description": "The child sees the light",
                       "camera": "medium shot", "lighting": "golden hour",
                       "characters": [{"id": "protagonist", "outfit_id": "raincoat",
                                       "state": "dry", "position": "center"}],
                       "video_prompt": "The protagonist in a raincoat sees the light"}]}
    write_checkpoint(pipeline_dir, "film-1", "shot_planning", "completed",
                     {"film_shot_plan": plan}, pipeline_type="character-film")
    keyframe_path = project_dir / "assets" / "keyframes" / "shot-1.png"
    keyframe_path.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), "orange").save(keyframe_path)
    review = {"verdict": "pass", "reviewer": "agent", "notes": "fixture review"}
    keyframes = {"version": "1.0", "shot_plan_fingerprint": artifact_fingerprint(plan),
                 "frames": [{"shot_id": "shot-1", "path": "assets/keyframes/shot-1.png",
                             "sha256": hashlib.sha256(keyframe_path.read_bytes()).hexdigest(),
                             "provider": "fixture", "model": "fixture", "prompt": "test",
                             "continuity_review": review, "creative_review": review}]}
    write_checkpoint(pipeline_dir, "film-1", "keyframe_generation", "completed",
                     {"film_keyframes": keyframes}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "video_generation"

    (refs / "raincoat.png").write_bytes(b"changed after approval")
    assert get_completed_stages(pipeline_dir, "film-1", "character-film") == [
        "story_development", "character_discovery", "character_distillation",
    ]
    Image.new("RGB", (16, 16), "blue").save(refs / "raincoat.png")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "video_generation"

    changed_cast = copy.deepcopy(cast)
    changed_cast["characters"][0]["role"] = "co-lead"
    write_checkpoint(pipeline_dir, "film-1", "character_discovery", "completed",
                     {"character_bible": changed_cast}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "character_distillation"
    write_checkpoint(pipeline_dir, "film-1", "character_discovery", "completed",
                     {"character_bible": cast}, pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "video_generation"

    # Reapproval of the changed story invalidates both downstream checkpoints.
    changed = revise_story(approved_story, {"premise": "The message changes."})
    changed["status"] = "AWAITING_APPROVAL"
    changed = lock_story(changed, "user")
    write_checkpoint(pipeline_dir, "film-1", "story_development", "completed",
                     {"story_bible": changed}, pipeline_type="character-film")
    assert get_completed_stages(pipeline_dir, "film-1", "character-film") == ["story_development"]
    assert get_next_stage(pipeline_dir, "film-1", "character-film") == "character_discovery"
    with pytest.raises(CheckpointValidationError):
        write_checkpoint(pipeline_dir, "film-1", "character_lock", "completed",
                         {"character_bible": ready}, pipeline_type="character-film")


def test_cast_must_match_story(tmp_path):
    approved_story = lock_story(story(), "user")
    cast = bible(approved_story)
    cast["characters"][0]["id"] = "different"
    from lib.character_film_state import validate_character_bible
    with pytest.raises(FilmStateError, match="cover exactly"):
        validate_character_bible(cast, approved_story, tmp_path, require_locked=False)
