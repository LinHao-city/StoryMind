"""Deterministic story and character gates for the character-film pipeline.

Creative decisions remain with the agent and user. These helpers only enforce
approval, file, and privacy invariants before a stage can advance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from PIL import Image

from schemas.artifacts import validate_artifact


class FilmStateError(ValueError):
    """A requested state transition violates a character-film invariant."""


def artifact_fingerprint(artifact: dict[str, Any]) -> str:
    """Hash JSON content, independent of dictionary insertion order."""
    payload = json.dumps(artifact, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def story_fingerprint(story: dict[str, Any]) -> str:
    """Fingerprint approved story content and revision, excluding approval metadata."""
    content = {key: value for key, value in story.items() if key not in {"status", "approval"}}
    return artifact_fingerprint(content)


def revise_story(story: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    if any(key in changes for key in ("version", "revision", "status", "approval")):
        raise FilmStateError("Story revision cannot set system-managed fields")
    revised = copy.deepcopy(story)
    revised.update(copy.deepcopy(changes))
    revised["revision"] = story["revision"] + 1
    revised["status"] = "DRAFT"
    revised.pop("approval", None)
    validate_artifact("story_bible", revised)
    return revised


def lock_story(story: dict[str, Any], approved_by: str, approved_at: str | None = None) -> dict[str, Any]:
    validate_artifact("story_bible", story)
    if story["status"] != "AWAITING_APPROVAL":
        raise FilmStateError("Story must await explicit approval before lock")
    if approved_by != "user":
        raise FilmStateError("Story lock requires explicit user approval")
    locked = copy.deepcopy(story)
    locked["status"] = "LOCKED"
    locked["approval"] = {
        "approved_by": approved_by,
        "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
    }
    validate_artifact("story_bible", locked)
    return locked


def validate_locked_story(story: dict[str, Any]) -> None:
    validate_artifact("story_bible", story)
    if story["status"] != "LOCKED" or story.get("approval", {}).get("approved_by") != "user":
        raise FilmStateError("Story is not explicitly user-approved and locked")


def validate_source_privacy(character: dict[str, Any]) -> None:
    source = character["source"]
    if source["source_photos_local_only"] and source["remote_character_creation_allowed"]:
        raise FilmStateError("Local-only source photos cannot be sent to remote character creation")
    if source["source_photos_local_only"] and source["downstream_use_original_photos"]:
        raise FilmStateError("Local-only source photos cannot be used downstream")
    if source["type"] in {"private_family_photo", "other_photo"} and source["remote_character_creation_allowed"]:
        approval = source.get("remote_character_creation_approval") or {}
        if approval.get("approved_by") != "user" or not approval.get("provider"):
            raise FilmStateError("Remote character creation from photos requires explicit user and provider approval")
    if source["downstream_use_original_photos"] and not source.get("downstream_original_approval"):
        raise FilmStateError("Original-photo downstream use requires explicit provider approval")
    if source["downstream_use_original_photos"]:
        approval = source["downstream_original_approval"]
        if approval.get("approved_by") != "user" or not approval.get("provider"):
            raise FilmStateError("Original-photo downstream use requires explicit user and provider approval")
    if source["type"] == "private_family_photo" and source["privacy_classification"] != "FAMILY_PRIVATE":
        raise FilmStateError("Private family photos must be classified FAMILY_PRIVATE")


def _require_project_file(project_dir: Path, relative_path: str, label: str) -> Path:
    root = project_dir.resolve()
    if not relative_path:
        raise FilmStateError(f"{label} is required")
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise FilmStateError(f"{label} must be an existing file inside the project: {relative_path}")
    return candidate


def _file_hash(project_dir: Path, relative_path: str, label: str) -> str:
    path = _require_project_file(project_dir, relative_path, label)
    if "source" in path.relative_to(project_dir.resolve()).parts:
        raise FilmStateError(f"{label} cannot use an original source photo")
    try:
        with Image.open(path) as image:
            image.verify()
    except (OSError, ValueError) as exc:
        raise FilmStateError(f"{label} must be a valid image") from exc
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    for source_dir in (project_dir.resolve() / "characters").glob("*/source"):
        if source_dir.is_dir() and any(
            hashlib.sha256(source.read_bytes()).hexdigest() == digest
            for source in source_dir.iterdir() if source.is_file()
        ):
            raise FilmStateError(f"{label} cannot reuse original source-photo bytes")
    return digest


def validate_character_lock(character: dict[str, Any], project_dir: Path) -> None:
    validate_source_privacy(character)
    if character.get("status") != "LOCKED" or character.get("identity_locked") is not True:
        raise FilmStateError(f"Character {character['id']} is not locked")
    if character.get("approval", {}).get("approved_by") != "user":
        raise FilmStateError(f"Character {character['id']} lacks explicit user approval")
    identity = character["identity"]
    for name, label in (("master", "master identity"), ("full_body", "full body reference")):
        current_hash = _file_hash(project_dir, identity.get(name, ""), label)
        if character.get("identity_hashes", {}).get(name) != current_hash:
            raise FilmStateError(f"{label} changed after character lock")
    if not character["required_outfits"]:
        raise FilmStateError(f"Character {character['id']} needs at least one required outfit")
    for outfit_id in character["required_outfits"]:
        outfit = character["outfits"].get(outfit_id)
        if not outfit or outfit.get("locked") is not True:
            raise FilmStateError(f"Required outfit {outfit_id!r} is not locked")
        current_hash = _file_hash(project_dir, outfit.get("reference", ""), f"outfit {outfit_id!r}")
        if outfit.get("reference_sha256") != current_hash:
            raise FilmStateError(f"Outfit {outfit_id!r} changed after character lock")


def lock_character(
    character: dict[str, Any], project_dir: Path, approved_by: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    if character.get("status") != "AWAITING_APPROVAL":
        raise FilmStateError("Character must await approval before lock")
    if approved_by != "user":
        raise FilmStateError("Character lock requires explicit user approval")
    locked = copy.deepcopy(character)
    locked["status"] = "LOCKED"
    locked["identity_locked"] = True
    locked["approval"] = {
        "approved_by": approved_by,
        "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
    }
    identity = locked["identity"]
    locked["identity_hashes"] = {
        name: _file_hash(project_dir, identity.get(name, ""), label)
        for name, label in (("master", "master identity"), ("full_body", "full body reference"))
    }
    for outfit_id in locked["required_outfits"]:
        outfit = locked["outfits"].get(outfit_id)
        if outfit is None or outfit.get("locked") is not True:
            raise FilmStateError(f"Required outfit {outfit_id!r} is not locked")
        outfit["reference_sha256"] = _file_hash(project_dir, outfit.get("reference", ""), f"outfit {outfit_id!r}")
    validate_character_lock(locked, project_dir)
    return locked


def validate_character_bible(bible: dict[str, Any], story: dict[str, Any], project_dir: Path, *, require_locked: bool) -> None:
    validate_artifact("character_bible", bible)
    validate_locked_story(story)
    if bible["story_fingerprint"] != story_fingerprint(story):
        raise FilmStateError("Character bible was built from an older story revision")
    ids = [character["id"] for character in bible["characters"]]
    if len(ids) != len(set(ids)):
        raise FilmStateError("Character IDs must be unique")
    if set(ids) != set(story["characters"]):
        raise FilmStateError("Character bible must cover exactly the story characters")
    for character in bible["characters"]:
        validate_source_privacy(character)
        if require_locked:
            validate_character_lock(character, project_dir)


def validate_candidate_selections(
    selections: dict[str, Any], story: dict[str, Any],
    bible: dict[str, Any], project_dir: Path,
) -> None:
    """Require one user-selected generated candidate per story character."""
    validate_artifact("character_candidates", selections)
    validate_character_bible(bible, story, project_dir, require_locked=False)
    if selections["story_fingerprint"] != story_fingerprint(story):
        raise FilmStateError("Character candidates were built from an older story")
    by_id = {character["id"]: character for character in bible["characters"]}
    ids = [entry["character_id"] for entry in selections["selections"]]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise FilmStateError("Character candidate selections must cover each story character once")
    for entry in selections["selections"]:
        character_id = entry["character_id"]
        if entry["fictionalization_level"] != by_id[character_id]["fictionalization_level"]:
            raise FilmStateError(f"Fictionalization level changed for {character_id}")
        candidate_ids = [candidate["id"] for candidate in entry["candidates"]]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise FilmStateError(f"Duplicate candidate ID for {character_id}")
        if entry["selected_candidate_id"] not in candidate_ids:
            raise FilmStateError(f"Selected candidate missing for {character_id}")
        for candidate in entry["candidates"]:
            asset = candidate["asset"]
            expected_dir = (project_dir.resolve() / "characters" / character_id / "candidate").resolve()
            path = _require_project_file(project_dir, asset["path"], "candidate image")
            if not path.is_relative_to(expected_dir):
                raise FilmStateError("Candidate image must be a generated project candidate, not a source photo")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise FilmStateError(f"Candidate image changed after selection for {character_id}")
            try:
                with Image.open(path) as image:
                    image.verify()
            except (OSError, ValueError) as exc:
                raise FilmStateError(f"Candidate is not a valid image for {character_id}") from exc
            for source_dir in (project_dir.resolve() / "characters").glob("*/source"):
                if source_dir.is_dir() and any(
                    hashlib.sha256(source.read_bytes()).hexdigest() == asset["sha256"]
                    for source in source_dir.iterdir() if source.is_file()
                ):
                    raise FilmStateError("Original source photo cannot be a generated candidate")
