"""Deterministic proposal, edit, render, and final review contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.character_film_state import FilmStateError, story_fingerprint
from schemas.artifacts import validate_artifact
from tools.video._shared import probe_output


def _project_file(project_dir: Path, name: str) -> Path:
    root = project_dir.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FilmStateError(f"Missing or escaping project file: {name}")
    return path


def validate_film_proposal(proposal: dict[str, Any], story: dict[str, Any]) -> None:
    validate_artifact("film_proposal", proposal)
    if proposal["story_fingerprint"] != story_fingerprint(story):
        raise FilmStateError("Production proposal targets an older story")
    if proposal["render_runtime"] not in proposal["options_considered"]:
        raise FilmStateError("Selected render runtime was not presented")
    if not {"remotion", "hyperframes"}.issubset(set(proposal["options_considered"])):
        raise FilmStateError("Proposal must record both composition runtimes")


def validate_film_edit(
    decisions: dict[str, Any], assets: dict[str, Any],
    clips: dict[str, Any], proposal: dict[str, Any], project_dir: Path,
) -> None:
    validate_artifact("edit_decisions", decisions)
    validate_artifact("asset_manifest", assets)
    if decisions["render_runtime"] != proposal["render_runtime"]:
        raise FilmStateError("Edit changed the approved render runtime")
    if decisions.get("renderer_family") != proposal["renderer_family"]:
        raise FilmStateError("Edit changed the approved renderer family")
    if decisions.get("composition_mode") != proposal["composition_mode"]:
        raise FilmStateError("Edit changed the approved composition mode")
    clip_ids = [clip["shot_id"] for clip in clips["clips"]]
    cuts = decisions["cuts"]
    if [cut["source"] for cut in cuts] != clip_ids:
        raise FilmStateError("Edit cuts must follow every approved clip in order")
    asset_by_id = {asset["id"]: asset for asset in assets["assets"]}
    if len(asset_by_id) != len(clip_ids) or set(asset_by_id) != set(clip_ids):
        raise FilmStateError("Asset manifest must contain exactly the approved clips")
    for clip, cut in zip(clips["clips"], cuts):
        asset = asset_by_id[clip["shot_id"]]
        if asset["type"] != "video" or Path(asset["path"]).resolve() != (project_dir.resolve() / clip["path"]).resolve():
            raise FilmStateError(f"Edit asset mismatch: {clip['shot_id']}")
        path = _project_file(project_dir, clip["path"])
        duration = probe_output(path).get("duration_seconds", 0)
        if cut["in_seconds"] < 0 or cut["out_seconds"] <= cut["in_seconds"]:
            raise FilmStateError(f"Invalid trim: {clip['shot_id']}")
        if cut["out_seconds"] > duration + 0.1:
            raise FilmStateError(f"Trim exceeds clip duration: {clip['shot_id']}")


def validate_film_render(
    report: dict[str, Any], proposal: dict[str, Any], project_dir: Path,
) -> None:
    validate_artifact("render_report", report)
    if report.get("metadata", {}).get("render_runtime") != proposal["render_runtime"]:
        raise FilmStateError("Render runtime differs from the approved proposal")
    for output in report["outputs"]:
        path = _project_file(project_dir, output["path"])
        probe = probe_output(path)
        if output["format"] != "mp4" or not probe.get("video_codec"):
            raise FilmStateError("Final render failed MP4 technical probe")
        if probe.get("duration_seconds", 0) <= 0:
            raise FilmStateError("Final render has no playable duration")


def validate_film_final_review(
    review: dict[str, Any], report: dict[str, Any],
    proposal: dict[str, Any], project_dir: Path,
) -> None:
    validate_artifact("final_review", review)
    validate_film_render(report, proposal, project_dir)
    if review["status"] != "pass":
        raise FilmStateError("Final review must pass before delivery")
    if review["output_path"] != report["outputs"][0]["path"]:
        raise FilmStateError("Final review inspected a different output")
    checks = review["checks"]
    if not checks["technical_probe"].get("valid_container"):
        raise FilmStateError("Final review lacks a valid technical probe")
    if checks["visual_spotcheck"].get("frames_sampled", 0) < 4:
        raise FilmStateError("Final review needs four inspected frames")
    if checks["promise_preservation"].get("render_runtime_used") != proposal["render_runtime"]:
        raise FilmStateError("Final review detected a runtime swap")
    metadata = review.get("metadata", {})
    if not metadata.get("character_continuity_passed") or not metadata.get("wardrobe_continuity_passed"):
        raise FilmStateError("Final character and wardrobe continuity checks must pass")
