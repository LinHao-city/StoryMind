"""Deterministic shot and media gates; visual judgment remains with reviewers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image
from lib.character_film_state import FilmStateError, artifact_fingerprint, story_fingerprint, validate_character_bible
from schemas.artifacts import validate_artifact


def _project_file(project_dir: Path, relative_path: str) -> Path:
    root = project_dir.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FilmStateError(f"Missing or escaping project media: {relative_path}")
    return path


def validate_shot_plan(
    plan: dict[str, Any], story: dict[str, Any],
    bible: dict[str, Any], project_dir: Path,
) -> None:
    validate_artifact("film_shot_plan", plan)
    validate_character_bible(bible, story, project_dir, require_locked=True)
    if plan["story_fingerprint"] != story_fingerprint(story):
        raise FilmStateError("Shot plan targets an older story")
    scene_ids = {scene.get("id") for scene in story["scenes"]}
    characters = {character["id"]: character for character in bible["characters"]}
    seen_shots: set[str] = set()
    prior_state: dict[str, str] = {}
    for shot in plan["shots"]:
        if shot["id"] in seen_shots:
            raise FilmStateError(f"Duplicate shot ID: {shot['id']}")
        seen_shots.add(shot["id"])
        if shot["scene_id"] not in scene_ids or shot["location"] not in story["locations"]:
            raise FilmStateError(f"Unknown scene or location in shot {shot['id']}")
        shot_character_ids = [entry["id"] for entry in shot["characters"]]
        if len(shot_character_ids) != len(set(shot_character_ids)):
            raise FilmStateError(f"Duplicate character in shot {shot['id']}")
        for entry in shot["characters"]:
            character = characters.get(entry["id"])
            if character is None:
                raise FilmStateError(f"Unknown character {entry['id']} in shot {shot['id']}")
            if entry["outfit_id"] not in character["required_outfits"]:
                raise FilmStateError(f"Unapproved outfit {entry['outfit_id']} in shot {shot['id']}")
            previous = prior_state.get(entry["id"])
            if previous is not None and previous != entry["state"]:
                if entry["state"] not in character.get("required_state_changes", []):
                    raise FilmStateError(f"Undeclared state change for {entry['id']} in shot {shot['id']}")
            prior_state[entry["id"]] = entry["state"]
    duration = sum(shot["duration_seconds"] for shot in plan["shots"])
    if abs(duration - story["target_duration_seconds"]) > 0.5:
        raise FilmStateError("Shot durations must sum to the approved target duration")


def validate_keyframes(manifest: dict[str, Any], plan: dict[str, Any], project_dir: Path) -> None:
    validate_artifact("film_keyframes", manifest)
    if manifest["shot_plan_fingerprint"] != artifact_fingerprint(plan):
        raise FilmStateError("Keyframes target an older shot plan")
    shot_ids = {shot["id"] for shot in plan["shots"]}
    frame_ids = [frame["shot_id"] for frame in manifest["frames"]]
    if len(frame_ids) != len(set(frame_ids)) or set(frame_ids) != shot_ids:
        raise FilmStateError("Keyframes must cover every shot exactly once")
    for frame in manifest["frames"]:
        path = _project_file(project_dir, frame["path"])
        if "source" in path.relative_to(project_dir.resolve()).parts:
            raise FilmStateError("Original source photo cannot be a movie keyframe")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != frame["sha256"]:
            raise FilmStateError(f"Keyframe changed after approval: {frame['shot_id']}")
        for source_dir in (project_dir.resolve() / "characters").glob("*/source"):
            if source_dir.is_dir() and any(
                hashlib.sha256(source.read_bytes()).hexdigest() == digest
                for source in source_dir.iterdir() if source.is_file()
            ):
                raise FilmStateError("Original source photo cannot be reused as a movie keyframe")
        try:
            with Image.open(path) as image:
                image.verify()
        except OSError as exc:
            raise FilmStateError(f"Keyframe is not a valid image: {frame['shot_id']}") from exc
        for review_type in ("continuity_review", "creative_review"):
            if frame[review_type]["verdict"] != "pass":
                raise FilmStateError(f"Shot {frame['shot_id']} failed {review_type}")


def validate_clips(
    manifest: dict[str, Any], plan: dict[str, Any],
    keyframes: dict[str, Any], project_dir: Path,
) -> None:
    validate_artifact("film_clips", manifest)
    validate_keyframes(keyframes, plan, project_dir)
    if manifest["shot_plan_fingerprint"] != artifact_fingerprint(plan):
        raise FilmStateError("Clips target an older shot plan")
    if manifest["keyframes_fingerprint"] != artifact_fingerprint(keyframes):
        raise FilmStateError("Clips target older keyframes")
    shot_ids = {shot["id"] for shot in plan["shots"]}
    shots_by_id = {shot["id"]: shot for shot in plan["shots"]}
    clip_ids = [clip["shot_id"] for clip in manifest["clips"]]
    if len(clip_ids) != len(set(clip_ids)) or set(clip_ids) != shot_ids:
        raise FilmStateError("Approved clips must cover every shot exactly once")
    from tools.video._shared import probe_output
    for clip in manifest["clips"]:
        path = _project_file(project_dir, clip["path"])
        if path.suffix.lower() != ".mp4":
            raise FilmStateError(f"Clip is not MP4: {clip['shot_id']}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != clip["sha256"]:
            raise FilmStateError(f"Clip changed after approval: {clip['shot_id']}")
        probe = probe_output(path)
        if not probe.get("video_codec") or probe.get("duration_seconds", 0) <= 0:
            raise FilmStateError(f"Clip failed technical probe: {clip['shot_id']}")
        if probe["duration_seconds"] + 0.5 < shots_by_id[clip["shot_id"]]["duration_seconds"]:
            raise FilmStateError(f"Clip is too short for shot {clip['shot_id']}")
        for sample in clip["sample_frames"]:
            _project_file(project_dir, sample)
        for review_type in ("continuity_review", "creative_review"):
            if clip[review_type]["verdict"] != "pass":
                raise FilmStateError(f"Clip {clip['shot_id']} failed {review_type}")
