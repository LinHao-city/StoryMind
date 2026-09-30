"""Local media intake and provenance for character-film.

This module does not invoke an image provider. Agent-native generation happens
outside Python, then its output is registered here as a project asset.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from lib.character_film_state import FilmStateError, validate_source_privacy


_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _image_info(path: Path) -> tuple[str, int, int]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            fmt = image.format
            width, height = image.size
    except (OSError, ValueError) as exc:
        raise FilmStateError(f"Not a supported image: {path}") from exc
    if fmt not in _IMAGE_FORMATS or width < 1 or height < 1:
        raise FilmStateError(f"Unsupported image format or dimensions: {path}")
    return fmt, width, height


def _safe_project_path(project_dir: Path, relative_path: str) -> Path:
    root = project_dir.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise FilmStateError("Media path must remain inside the project")
    return path


def _character_id(character: dict[str, Any]) -> str:
    character_id = character["id"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", character_id):
        raise FilmStateError("Character ID must use lowercase kebab-case")
    return character_id


def _asset_record(project_dir: Path, path: Path, *, origin: str, **details: Any) -> dict[str, Any]:
    fmt, width, height = _image_info(path)
    return {
        "path": path.relative_to(project_dir.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "format": fmt.lower(), "width": width, "height": height,
        "origin": origin, **details,
    }


def intake_source_photo(
    project_dir: Path, character: dict[str, Any], input_path: Path,
) -> dict[str, Any]:
    """Copy one user photo locally; never contact a provider or log image bytes."""
    validate_source_privacy(character)
    source = input_path.resolve()
    if not source.is_file():
        raise FilmStateError(f"Source photo not found: {input_path}")
    fmt, _, _ = _image_info(source)
    character_id = _character_id(character)
    target_dir = _safe_project_path(project_dir, f"characters/{character_id}/source")
    target_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target = target_dir / f"source-{digest[:16]}{_IMAGE_FORMATS[fmt]}"
    if not target.exists():
        shutil.copyfile(source, target)
    return _asset_record(project_dir, target, origin="user_source")


def register_generated_image(
    project_dir: Path, character: dict[str, Any], input_path: Path,
    *, category: str, asset_id: str, provider: str, model: str,
    prompt: str, seed: int | None = None,
) -> dict[str, Any]:
    """Register a generated candidate, identity, or outfit image locally."""
    if category not in {"candidate", "identity", "outfit", "keyframe"}:
        raise FilmStateError("Unsupported generated image category")
    if not asset_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in asset_id):
        raise FilmStateError("Asset ID must use lowercase letters, digits, and hyphens")
    if not provider or not model or not prompt:
        raise FilmStateError("Generated image needs provider, model, and prompt provenance")
    source = input_path.resolve()
    if not source.is_file():
        raise FilmStateError(f"Generated image not found: {input_path}")
    fmt, _, _ = _image_info(source)
    character_id = _character_id(character)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    for source_dir in (project_dir.resolve() / "characters").glob("*/source"):
        if source_dir.is_dir() and any(
            hashlib.sha256(photo.read_bytes()).hexdigest() == digest
            for photo in source_dir.iterdir() if photo.is_file()
        ):
            raise FilmStateError("Source photo cannot be registered as a generated image")
    target_dir = _safe_project_path(project_dir, f"characters/{character_id}/{category}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{asset_id}{_IMAGE_FORMATS[fmt]}"
    if target.exists() and target.resolve() != source:
        raise FilmStateError(f"Asset already exists: {target}")
    if target.resolve() != source:
        shutil.copyfile(source, target)
    return _asset_record(
        project_dir, target, origin="generated", provider=provider,
        model=model, prompt=prompt, seed=seed,
    )


def validate_remote_source_use(character: dict[str, Any], provider: str) -> None:
    """Check explicit, provider-specific permission before a remote photo call."""
    validate_source_privacy(character)
    source = character["source"]
    if source["type"] not in {"private_family_photo", "other_photo"}:
        return
    approval = source.get("remote_character_creation_approval") or {}
    if (source["source_photos_local_only"] or not source["remote_character_creation_allowed"]
            or approval.get("approved_by") != "user" or approval.get("provider") != provider):
        raise FilmStateError(f"Remote source-photo use with {provider!r} is not approved")
