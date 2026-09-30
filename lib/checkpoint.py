"""Checkpoint writer/reader for pipeline state persistence.

Each stage writes a checkpoint after completion. The orchestrator uses
checkpoints to resume pipelines and to present state at human checkpoints.
"""

from __future__ import annotations

import json
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jsonschema

from schemas.artifacts import ARTIFACT_NAMES, validate_artifact

# All known stages across all pipelines (used only for artifact name lookup).
ALL_KNOWN_STAGES = frozenset([
    "research", "proposal", "idea", "script", "scene_plan",
    "assets", "edit", "compose", "publish",
])

# Backward-compatible alias — existing code / tests that import STAGES still work.
# New code should use get_pipeline_stages(pipeline_type) instead.
STAGES = ["research", "proposal", "idea", "script", "scene_plan",
          "assets", "edit", "compose", "publish"]

CANONICAL_STAGE_ARTIFACTS = {
    "research": "research_brief",
    "proposal": "proposal_packet",
    "idea": "brief",
    "script": "script",
    "scene_plan": "scene_plan",
    "assets": "asset_manifest",
    "edit": "edit_decisions",
    "compose": "render_report",
    "publish": "publish_log",
}

# Additional artifacts that may be produced alongside canonical ones.
# These are not stage-defining but are required by governance contracts.
SUPPLEMENTARY_ARTIFACTS = {
    "source_media_review",  # Required before first planning stage when user media exists
    "final_review",         # Required by compose stage before presenting to user
    "video_analysis_brief", # Reference-video grounding artifact carried alongside stages
}


def get_pipeline_stages(pipeline_type: str | None) -> list[str]:
    """Return the ordered stage list for a specific pipeline.

    Falls back to STAGES (deterministic canonical order) when pipeline_type
    is not provided or the manifest cannot be loaded.

    Previous versions used a set intersection here, which produced
    nondeterministic ordering. The fallback now uses a stable list.
    """
    if pipeline_type is None:
        # Deterministic canonical fallback — sorted to ensure stable ordering
        import logging
        logging.getLogger(__name__).warning(
            "get_pipeline_stages called without pipeline_type — "
            "using canonical fallback order. Pass pipeline_type for correctness."
        )
        return list(STAGES)

    try:
        from lib.pipeline_loader import load_pipeline, get_stage_order
        manifest = load_pipeline(pipeline_type)
        return get_stage_order(manifest)
    except (FileNotFoundError, Exception):
        # Graceful fallback: return all known stages in canonical order
        return list(STAGES)

CHECKPOINT_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "checkpoints"
    / "checkpoint.schema.json"
)


class CheckpointValidationError(ValueError):
    """Raised when a checkpoint or its canonical artifacts are invalid."""


@lru_cache(maxsize=1)
def _load_checkpoint_schema() -> dict[str, Any]:
    with open(CHECKPOINT_SCHEMA_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def _validate_artifacts_for_stage(
    stage: str,
    status: str,
    artifacts: dict[str, Any],
    pipeline_type: str | None = None,
) -> None:
    required_artifact = CANONICAL_STAGE_ARTIFACTS.get(stage)
    if pipeline_type and pipeline_type != "unknown":
        from lib.pipeline_loader import load_pipeline
        manifest = load_pipeline(pipeline_type)
        definition = next((item for item in manifest["stages"] if item["name"] == stage), None)
        if definition:
            produced = definition.get("produces", [])
            required_artifact = produced[0] if produced else None
    if required_artifact is None:
        raise CheckpointValidationError(f"Stage {stage!r} has no canonical artifact")
    if status in {"completed", "awaiting_human"} and required_artifact not in artifacts:
        raise CheckpointValidationError(
            f"Stage {stage!r} with status {status!r} must include "
            f"canonical artifact {required_artifact!r}"
        )
    if (pipeline_type == "character-film" and stage == "edit"
            and status in {"completed", "awaiting_human"}
            and "asset_manifest" not in artifacts):
        raise CheckpointValidationError("Film edit requires asset_manifest alongside edit_decisions")

    for artifact_name, artifact_data in artifacts.items():
        if artifact_name not in ARTIFACT_NAMES:
            continue
        if not isinstance(artifact_data, dict):
            raise CheckpointValidationError(
                f"Artifact {artifact_name!r} must be a JSON object matching its schema"
            )
        try:
            validate_artifact(artifact_name, artifact_data)
        except Exception as exc:
            raise CheckpointValidationError(
                f"Artifact {artifact_name!r} failed schema validation: {exc}"
            ) from exc


def validate_checkpoint(checkpoint: dict[str, Any]) -> None:
    """Validate checkpoint structure and canonical artifact payloads.

    Uses pipeline_type (if present) to resolve the valid stage list.
    Falls back to ALL_KNOWN_STAGES when pipeline_type is absent.
    """
    stage = checkpoint.get("stage")
    status = checkpoint.get("status")
    artifacts = checkpoint.get("artifacts")
    pipeline_type = checkpoint.get("pipeline_type")

    valid_stages = (
        set(get_pipeline_stages(pipeline_type)) if pipeline_type
        else ALL_KNOWN_STAGES
    )

    if not isinstance(stage, str) or stage not in valid_stages:
        raise CheckpointValidationError(
            f"Invalid stage: {stage!r} for pipeline {pipeline_type!r}. "
            f"Valid stages: {sorted(valid_stages)}"
        )
    if not isinstance(status, str):
        raise CheckpointValidationError(f"Invalid status: {status!r}")
    if not isinstance(artifacts, dict):
        raise CheckpointValidationError("Checkpoint artifacts must be a dictionary")

    _validate_artifacts_for_stage(stage, status, artifacts, pipeline_type)

    if pipeline_type == "character-film" and status in {"completed", "awaiting_human"}:
        from lib.character_film_state import FilmStateError, validate_locked_story
        if stage == "story_development":
            story = artifacts["story_bible"]
            if status == "completed":
                try:
                    validate_locked_story(story)
                except FilmStateError as exc:
                    raise CheckpointValidationError(str(exc)) from exc
            elif story["status"] != "AWAITING_APPROVAL":
                raise CheckpointValidationError("Story awaiting approval must have AWAITING_APPROVAL status")

    try:
        jsonschema.validate(instance=checkpoint, schema=_load_checkpoint_schema())
    except jsonschema.ValidationError as exc:
        raise CheckpointValidationError(f"Checkpoint failed schema validation: {exc.message}") from exc


def _checkpoint_path(pipeline_dir: Path, project_id: str, stage: str) -> Path:
    return pipeline_dir / project_id / f"checkpoint_{stage}.json"


def _character_film_inputs(
    pipeline_dir: Path, project_id: str, stage: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Read the latest completed upstream artifacts and their fingerprints."""
    from lib.character_film_state import artifact_fingerprint
    from lib.pipeline_loader import load_pipeline

    manifest = load_pipeline("character-film")
    definition = next(item for item in manifest["stages"] if item["name"] == stage)
    needed = definition.get("required_artifacts_in", [])
    prior = []
    for item in manifest["stages"]:
        if item["name"] == stage:
            break
        prior.append(item["name"])
    current = get_completed_stages(pipeline_dir, project_id, "character-film")
    if current[:len(prior)] != prior:
        raise CheckpointValidationError(
            f"Stage {stage!r} requires current completed stages {prior}; found {current}"
        )
    artifacts: dict[str, Any] = {}
    for prior_stage in reversed(prior):
        cp = read_checkpoint(pipeline_dir, project_id, prior_stage)
        if cp is None or cp["status"] != "completed" or cp.get("pipeline_type") != "character-film":
            continue
        for name in needed:
            if name not in artifacts and name in cp["artifacts"]:
                artifacts[name] = cp["artifacts"][name]
    missing = set(needed) - set(artifacts)
    if missing:
        raise CheckpointValidationError(f"Missing completed upstream artifacts: {sorted(missing)}")
    return artifacts, {name: artifact_fingerprint(value) for name, value in artifacts.items()}


def _validate_character_film_transition(
    pipeline_dir: Path, project_id: str, stage: str, status: str,
    artifacts: dict[str, Any], metadata: dict[str, Any],
) -> None:
    if stage == "story_development" or status not in {"completed", "awaiting_human"}:
        return
    from lib.character_film_state import FilmStateError, validate_candidate_selections, validate_character_bible
    upstream, fingerprints = _character_film_inputs(pipeline_dir, project_id, stage)
    metadata["input_fingerprints"] = fingerprints
    bible = artifacts.get("character_bible")
    if bible is not None:
        try:
            validate_character_bible(
                bible, upstream["story_bible"],
                pipeline_dir.parent / "projects" / project_id,
                require_locked=(stage == "character_lock" and status == "completed"),
            )
        except FilmStateError as exc:
            raise CheckpointValidationError(str(exc)) from exc
    if stage == "character_distillation":
        try:
            validate_candidate_selections(
                artifacts["character_candidates"], upstream["story_bible"],
                upstream["character_bible"], pipeline_dir.parent / "projects" / project_id,
            )
        except FilmStateError as exc:
            raise CheckpointValidationError(str(exc)) from exc
    if stage == "character_lock" and status == "completed":
        selected = {entry["character_id"]: entry["selected_candidate_id"]
                    for entry in upstream["character_candidates"]["selections"]}
        if any(character.get("selected_candidate_id") != selected.get(character["id"])
               for character in bible["characters"]):
            raise CheckpointValidationError("Locked characters must identify their approved candidate")
    if stage in {"shot_planning", "keyframe_generation"}:
        from lib.film_continuity import validate_keyframes, validate_shot_plan
        try:
            project_dir = pipeline_dir.parent / "projects" / project_id
            if stage == "shot_planning":
                validate_shot_plan(
                    artifacts["film_shot_plan"], upstream["story_bible"],
                    upstream["character_bible"], project_dir,
                )
            else:
                validate_keyframes(
                    artifacts["film_keyframes"], upstream["film_shot_plan"], project_dir,
                )
        except FilmStateError as exc:
            raise CheckpointValidationError(str(exc)) from exc
    if stage == "video_generation":
        from lib.film_continuity import validate_clips
        try:
            validate_clips(
                artifacts["film_clips"], upstream["film_shot_plan"],
                upstream["film_keyframes"], pipeline_dir.parent / "projects" / project_id,
            )
        except FilmStateError as exc:
            raise CheckpointValidationError(str(exc)) from exc
    if stage in {"proposal", "edit", "compose", "final_review"}:
        from lib.film_delivery import (
            validate_film_edit, validate_film_final_review,
            validate_film_proposal, validate_film_render,
        )
        try:
            project_dir = pipeline_dir.parent / "projects" / project_id
            if stage == "proposal":
                validate_film_proposal(artifacts["film_proposal"], upstream["story_bible"])
            elif stage == "edit":
                validate_film_edit(
                    artifacts["edit_decisions"], artifacts["asset_manifest"],
                    upstream["film_clips"], upstream["film_proposal"], project_dir,
                )
            elif stage == "compose":
                validate_film_render(artifacts["render_report"], upstream["film_proposal"], project_dir)
            else:
                validate_film_final_review(
                    artifacts["final_review"], upstream["render_report"],
                    upstream["film_proposal"], project_dir,
                )
        except FilmStateError as exc:
            raise CheckpointValidationError(str(exc)) from exc


def _decision_log_path(pipeline_dir: Path, project_id: str) -> Path:
    return pipeline_dir / project_id / "decision_log.json"


def _merge_decision_log(
    pipeline_dir: Path, project_id: str, new_log: dict[str, Any]
) -> None:
    """Append new decisions to the project-level decision log.

    Each stage may produce decisions. This function merges them into a
    single cumulative file so reviewers and the bench can inspect the
    full audit trail.
    """
    path = _decision_log_path(pipeline_dir, project_id)
    if path.exists():
        with open(path) as f:
            existing = json.load(f)
    else:
        existing = {
            "version": "1.0",
            "project_id": project_id,
            "decisions": [],
        }

    existing_ids = {d["decision_id"] for d in existing.get("decisions", [])}
    for decision in new_log.get("decisions", []):
        if decision.get("decision_id") not in existing_ids:
            existing["decisions"].append(decision)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def write_checkpoint(
    pipeline_dir: Path,
    project_id: str,
    stage: str,
    status: str,
    artifacts: dict[str, Any],
    *,
    pipeline_type: Optional[str] = None,
    style_playbook: Optional[str] = None,
    checkpoint_policy: str = "guided",
    human_approval_required: bool = False,
    human_approved: bool = False,
    review: Optional[dict] = None,
    cost_snapshot: Optional[dict] = None,
    error: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Path:
    """Write a checkpoint file for a pipeline stage."""
    valid_stages = (
        set(get_pipeline_stages(pipeline_type)) if pipeline_type
        else ALL_KNOWN_STAGES
    )
    if stage not in valid_stages:
        raise ValueError(
            f"Invalid stage: {stage!r} for pipeline {pipeline_type!r}. "
            f"Valid stages: {sorted(valid_stages)}"
        )

    checkpoint = {
        "version": "1.0",
        "project_id": project_id,
        "pipeline_type": pipeline_type or "unknown",
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checkpoint_policy": checkpoint_policy,
        "human_approval_required": human_approval_required,
        "human_approved": human_approved,
        "artifacts": artifacts,
    }
    if style_playbook is not None:
        checkpoint["style_playbook"] = style_playbook
    if review is not None:
        checkpoint["review"] = review
    if cost_snapshot is not None:
        checkpoint["cost_snapshot"] = cost_snapshot
    if error is not None:
        checkpoint["error"] = error
    checkpoint_metadata = dict(metadata or {})
    if pipeline_type == "character-film":
        # Validate the stage's own artifact contract before transition checks
        # dereference it. Missing output must surface as a checkpoint error.
        _validate_artifacts_for_stage(stage, status, artifacts, pipeline_type)
        _validate_character_film_transition(
            pipeline_dir, project_id, stage, status, artifacts, checkpoint_metadata,
        )
    if checkpoint_metadata:
        checkpoint["metadata"] = checkpoint_metadata

    # Merge decision_log: if this checkpoint carries new decisions,
    # append them to the project-level decision log file, then write the
    # reference back into relevant artifacts so downstream consumers can find it.
    if "decision_log" in artifacts and isinstance(artifacts["decision_log"], dict):
        _merge_decision_log(pipeline_dir, project_id, artifacts["decision_log"])
        log_ref = str(_decision_log_path(pipeline_dir, project_id))

        # Write decision_log_ref into proposal_packet and render_report
        # artifacts if they are present in this checkpoint.
        for artifact_key in ("proposal_packet", "render_report"):
            if artifact_key in artifacts and isinstance(artifacts[artifact_key], dict):
                plan_or_top = artifacts[artifact_key]
                # proposal_packet stores it under production_plan
                if artifact_key == "proposal_packet":
                    plan = plan_or_top.get("production_plan")
                    if isinstance(plan, dict):
                        plan["decision_log_ref"] = log_ref
                else:
                    plan_or_top["decision_log_ref"] = log_ref

    validate_checkpoint(checkpoint)

    path = _checkpoint_path(pipeline_dir, project_id, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(checkpoint, f, indent=2)

    return path


def read_checkpoint(
    pipeline_dir: Path, project_id: str, stage: str
) -> Optional[dict[str, Any]]:
    """Read a checkpoint file. Returns None if not found."""
    path = _checkpoint_path(pipeline_dir, project_id, stage)
    if not path.exists():
        return None
    with open(path) as f:
        checkpoint = json.load(f)
    validate_checkpoint(checkpoint)
    return checkpoint


def get_latest_checkpoint(
    pipeline_dir: Path, project_id: str
) -> Optional[dict[str, Any]]:
    """Find the most recent checkpoint for a project (by file mtime)."""
    project_dir = pipeline_dir / project_id
    if not project_dir.exists():
        return None

    checkpoints = sorted(
        project_dir.glob("checkpoint_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not checkpoints:
        return None

    with open(checkpoints[0]) as f:
        checkpoint = json.load(f)
    validate_checkpoint(checkpoint)
    return checkpoint


def get_completed_stages(
    pipeline_dir: Path, project_id: str, pipeline_type: str | None = None
) -> list[str]:
    """Return list of stages that have a completed checkpoint.

    When pipeline_type is provided, only checks stages defined in that
    pipeline's manifest — preventing false positives from leftover
    checkpoints of a different pipeline type.
    """
    stages_to_check = get_pipeline_stages(pipeline_type)
    completed = []
    if pipeline_type == "character-film":
        from lib.character_film_state import FilmStateError, validate_candidate_selections, validate_character_bible, validate_locked_story
        from lib.pipeline_loader import load_pipeline
        manifest = load_pipeline(pipeline_type)
        latest: dict[str, Any] = {}
        for definition in manifest["stages"]:
            stage = definition["name"]
            cp = read_checkpoint(pipeline_dir, project_id, stage)
            if cp is None or cp.get("pipeline_type") != pipeline_type or cp.get("status") != "completed":
                break
            expected = cp.get("metadata", {}).get("input_fingerprints", {})
            required = definition.get("required_artifacts_in", [])
            if required:
                from lib.character_film_state import artifact_fingerprint
                if any(name not in latest or expected.get(name) != artifact_fingerprint(latest[name]) for name in required):
                    break
            try:
                if stage == "story_development":
                    validate_locked_story(cp["artifacts"]["story_bible"])
                elif stage == "character_distillation":
                    validate_candidate_selections(
                        cp["artifacts"]["character_candidates"], latest["story_bible"],
                        latest["character_bible"], pipeline_dir.parent / "projects" / project_id,
                    )
                elif stage == "shot_planning":
                    from lib.film_continuity import validate_shot_plan
                    validate_shot_plan(
                        cp["artifacts"]["film_shot_plan"], latest["story_bible"],
                        latest["character_bible"], pipeline_dir.parent / "projects" / project_id,
                    )
                elif stage == "keyframe_generation":
                    from lib.film_continuity import validate_keyframes
                    validate_keyframes(
                        cp["artifacts"]["film_keyframes"], latest["film_shot_plan"],
                        pipeline_dir.parent / "projects" / project_id,
                    )
                elif stage == "video_generation":
                    from lib.film_continuity import validate_clips
                    validate_clips(
                        cp["artifacts"]["film_clips"], latest["film_shot_plan"],
                        latest["film_keyframes"], pipeline_dir.parent / "projects" / project_id,
                    )
                elif stage in {"proposal", "edit", "compose", "final_review"}:
                    from lib.film_delivery import (
                        validate_film_edit, validate_film_final_review,
                        validate_film_proposal, validate_film_render,
                    )
                    project_dir = pipeline_dir.parent / "projects" / project_id
                    if stage == "proposal":
                        validate_film_proposal(cp["artifacts"]["film_proposal"], latest["story_bible"])
                    elif stage == "edit":
                        validate_film_edit(
                            cp["artifacts"]["edit_decisions"], cp["artifacts"]["asset_manifest"],
                            latest["film_clips"], latest["film_proposal"], project_dir,
                        )
                    elif stage == "compose":
                        validate_film_render(cp["artifacts"]["render_report"], latest["film_proposal"], project_dir)
                    else:
                        validate_film_final_review(
                            cp["artifacts"]["final_review"], latest["render_report"],
                            latest["film_proposal"], project_dir,
                        )
                elif "character_bible" in cp["artifacts"]:
                    validate_character_bible(
                        cp["artifacts"]["character_bible"], latest["story_bible"],
                        pipeline_dir.parent / "projects" / project_id,
                        require_locked=(stage == "character_lock"),
                    )
                    if stage == "character_lock":
                        selected = {entry["character_id"]: entry["selected_candidate_id"]
                                    for entry in latest["character_candidates"]["selections"]}
                        if any(character.get("selected_candidate_id") != selected.get(character["id"])
                               for character in cp["artifacts"]["character_bible"]["characters"]):
                            break
            except FilmStateError:
                break
            latest.update(cp["artifacts"])
            completed.append(stage)
        return completed
    for stage in stages_to_check:
        cp = read_checkpoint(pipeline_dir, project_id, stage)
        if cp and cp.get("status") == "completed":
            completed.append(stage)
    return completed


def get_next_stage(
    pipeline_dir: Path, project_id: str, pipeline_type: str | None = None
) -> Optional[str]:
    """Determine the next stage to run based on completed checkpoints.

    Uses pipeline-specific stage order so that pipelines with different
    stage sequences (e.g. cinematic vs explainer) progress correctly.
    """
    stages = get_pipeline_stages(pipeline_type) if pipeline_type else STAGES
    completed = set(get_completed_stages(pipeline_dir, project_id, pipeline_type))
    for stage in stages:
        if stage not in completed:
            return stage
    return None
