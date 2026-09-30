"""Privacy-gated reference routing for character-film video shots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.character_film_state import FilmStateError, validate_character_bible
from lib.film_continuity import validate_keyframes, validate_shot_plan
from lib.film_delivery import validate_film_proposal
from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile, RetryPolicy,
    ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier,
)


def _local(project_dir: Path, relative: str) -> str:
    root = project_dir.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise FilmStateError(f"Missing project reference: {relative}")
    if "source" in path.relative_to(root).parts:
        raise FilmStateError("Original source photos cannot be routed to film video")
    return str(path)


def plan_film_video_call(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate one approved shot and return an upload-free provider plan."""
    project_dir = Path(inputs["project_dir"])
    story, bible = inputs["story_bible"], inputs["character_bible"]
    proposal = inputs["film_proposal"]
    shot_plan, keyframes = inputs["film_shot_plan"], inputs["film_keyframes"]
    validate_character_bible(bible, story, project_dir, require_locked=True)
    validate_film_proposal(proposal, story)
    validate_shot_plan(shot_plan, story, bible, project_dir)
    validate_keyframes(keyframes, shot_plan, project_dir)
    shot = next((item for item in shot_plan["shots"] if item["id"] == inputs["shot_id"]), None)
    if shot is None:
        raise FilmStateError("Shot ID is not in the approved shot plan")
    frame = next(item for item in keyframes["frames"] if item["shot_id"] == shot["id"])
    provider = inputs["provider"]
    policy = inputs["provider_policy"]
    if proposal.get("provider_policy") != policy or policy.get("budget_usd") != proposal["budget_usd"]:
        raise FilmStateError("Video policy must match the user-approved proposal and budget")
    if provider not in {"kling", "seedance"}:
        raise FilmStateError(f"Unsupported film provider: {provider}")
    if provider in policy.get("policy_rejected_providers", []):
        raise FilmStateError("Provider was policy-rejected; human decision required")
    if policy.get("approved_provider") != provider or policy.get("approved_by") != "user":
        raise FilmStateError("Video provider requires explicit user approval")
    if policy.get("model_variant") != inputs.get("model_variant"):
        raise FilmStateError("Model variant differs from the approved production plan")
    private = any(character["source"]["privacy_classification"] != "PUBLIC"
                  for character in bible["characters"])
    output_approval = policy.get("public_output_approval") or {}
    if private and not (output_approval.get("approved_by") == "user"
                        and output_approval.get("provider") == provider):
        raise FilmStateError("Provider returns an accessible output URL; private project requires explicit acceptance")
    references = []
    by_id = {character["id"]: character for character in bible["characters"]}
    for entry in shot["characters"]:
        character = by_id[entry["id"]]
        references.append({
            "character_id": entry["id"],
            "frontal": _local(project_dir, character["identity"]["master"]),
            "full_body": _local(project_dir, character["identity"]["full_body"]),
            "outfit": _local(project_dir, character["outfits"][entry["outfit_id"]]["reference"]),
        })
    duration = round(shot["duration_seconds"])
    if provider == "kling" and not 3 <= duration <= 15:
        raise FilmStateError("Kling v3 shot duration must be 3-15 seconds")
    if provider == "seedance" and not 4 <= duration <= 15:
        raise FilmStateError("Seedance shot duration must be 4-15 seconds")
    if provider == "seedance" and 1 + 2 * len(references) > 9:
        raise FilmStateError("Seedance shot exceeds the nine-image reference limit")
    return {
        "provider": provider, "model_variant": inputs["model_variant"],
        "shot_id": shot["id"], "duration": str(duration),
        "aspect_ratio": "16:9",
        "resolution": "720p" if provider == "seedance" else None,
        "generate_audio": bool(policy.get("generate_audio", False)),
        "prompt": shot["video_prompt"],
        "start_keyframe": _local(project_dir, frame["path"]),
        "characters": references,
        "output_path": str(project_dir.resolve() / "assets" / "video" / f"{shot['id']}.mp4"),
        "output_access": "provider_url_may_be_public",
    }


def rank_film_providers(requirements: dict[str, Any]) -> list[dict[str, Any]]:
    """Explain eligibility without selecting or invoking a provider."""
    from tools.video.kling_video import KlingVideo
    from tools.video.seedance_video import SeedanceVideo
    duration = int(requirements.get("duration_seconds", 5))
    private = bool(requirements.get("private_characters", False))
    rejected = set(requirements.get("policy_rejected_providers", []))
    output_approvals = requirements.get("public_output_approvals", {})
    max_call_cost = requirements.get("max_call_cost_usd", 0)
    options = []
    for provider, tool, variant in (
        ("kling", KlingVideo(), "v3/standard"),
        ("seedance", SeedanceVideo(), "standard"),
    ):
        reasons = []
        if tool.get_status() != ToolStatus.AVAILABLE:
            reasons.append("provider not configured")
        if provider in rejected:
            reasons.append("previous policy rejection; requires human decision")
        if provider == "kling" and not 3 <= duration <= 15:
            reasons.append("duration outside Kling v3 range")
        if provider == "seedance" and not 4 <= duration <= 15:
            reasons.append("duration outside Seedance range")
        approval = output_approvals.get(provider) or {}
        if private and approval.get("approved_by") != "user":
            reasons.append("public output access not approved")
        estimated = tool.estimate_cost({
            "duration": str(duration), "model_variant": variant,
            "generate_audio": bool(requirements.get("generate_audio", False)),
        })
        if estimated > max_call_cost:
            reasons.append("estimated cost exceeds per-shot limit")
        options.append({
            "provider": provider, "tool": tool.name, "model_variant": variant,
            "estimated_cost_usd": estimated, "eligible": not reasons,
            "reasons": reasons, "output_access": "provider_url_may_be_public",
        })
    return sorted(options, key=lambda item: (not item["eligible"], item["estimated_cost_usd"]))


class FilmProviderRouter(BaseTool):
    name = "film_provider_router"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "film_video_generation"
    provider = "selector"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.HYBRID
    capabilities = ["character_reference_routing", "video_privacy_gate"]
    supports = {"character_elements": True, "provider_specific_approval": True}
    agent_skills = ["ai-video-gen"]
    input_schema = {
        "type": "object", "required": ["operation"],
        "properties": {
            "operation": {"enum": ["rank", "plan", "generate"]},
            "requirements": {"type": "object"},
            "project_dir": {"type": "string"}, "story_bible": {"type": "object"},
            "film_proposal": {"type": "object"},
            "character_bible": {"type": "object"}, "film_shot_plan": {"type": "object"},
            "film_keyframes": {"type": "object"}, "shot_id": {"type": "string"},
            "provider": {"enum": ["kling", "seedance"]},
            "model_variant": {"type": "string"}, "provider_policy": {"type": "object"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, disk_mb=1000, network_required=True)
    retry_policy = RetryPolicy(max_retries=0)
    side_effects = ["generate uploads approved derived references and calls a paid provider"]

    def get_status(self) -> ToolStatus:
        from tools.video.kling_video import KlingVideo
        from tools.video.seedance_video import SeedanceVideo
        return (ToolStatus.AVAILABLE if any(tool.get_status() == ToolStatus.AVAILABLE
                for tool in (KlingVideo(), SeedanceVideo())) else ToolStatus.UNAVAILABLE)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            if inputs["operation"] == "rank":
                return ToolResult(success=True, data={
                    "options": rank_film_providers(inputs.get("requirements", {})),
                    "selection": "user approval required before plan or generate",
                })
            plan = plan_film_video_call(inputs)
            if inputs["operation"] == "plan":
                return ToolResult(success=True, data={"plan": plan})
            if inputs["operation"] != "generate":
                return ToolResult(success=False, error="Unsupported operation")
            from tools.video._shared import upload_image_fal
            from tools.video.kling_video import KlingVideo
            from tools.video.seedance_video import SeedanceVideo
            provider_tool = KlingVideo() if plan["provider"] == "kling" else SeedanceVideo()
            if provider_tool.get_status() != ToolStatus.AVAILABLE:
                return ToolResult(success=False, error=f"{plan['provider']} is not configured")
            call: dict[str, Any] = {
                "prompt": plan["prompt"], "model_variant": plan["model_variant"],
                "duration": plan["duration"], "output_path": plan["output_path"],
                "aspect_ratio": plan["aspect_ratio"],
                "generate_audio": plan["generate_audio"],
            }
            if plan["resolution"]:
                call["resolution"] = plan["resolution"]
            estimate = provider_tool.estimate_cost(call)
            policy = inputs["provider_policy"]
            if estimate > policy.get("max_call_cost_usd", 0):
                return ToolResult(success=False, error="Call exceeds approved per-shot budget")
            if policy.get("budget_usd", 0) <= 0:
                return ToolResult(success=False, error="Project budget requires explicit approval")
            from lib.config_model import BudgetMode
            from tools.cost_tracker import CostTracker, ApprovalRequiredError, BudgetExceededError
            cost_log = Path(inputs["project_dir"]) / "artifacts" / "film_cost_log.json"
            tracker = CostTracker(
                budget_total_usd=policy["budget_usd"], reserve_pct=0,
                single_action_approval_usd=policy["max_call_cost_usd"],
                require_approval_for_new_paid_tool=False, mode=BudgetMode.CAP,
                cost_log_path=cost_log,
            )
            entry_id = tracker.estimate(provider_tool.name, "film_shot", estimate)
            try:
                tracker.reserve(entry_id)
            except (ApprovalRequiredError, BudgetExceededError) as exc:
                return ToolResult(success=False, error=str(exc))
            # Every image reaching fal is a checked derived reference.
            paid_call_started = False
            try:
                start_url = upload_image_fal(plan["start_keyframe"])
                if plan["provider"] == "kling":
                    call["operation"] = "image_to_video"
                    call["start_image_url"] = start_url
                    elements = []
                    for index, reference in enumerate(plan["characters"], 1):
                        elements.append({
                            "frontal_image_url": upload_image_fal(reference["frontal"]),
                            "reference_image_urls": [
                                upload_image_fal(reference["full_body"]),
                                upload_image_fal(reference["outfit"]),
                            ],
                        })
                        call["prompt"] += f" @Element{index} is {reference['character_id']}."
                    if elements:
                        call["elements"] = elements
                else:
                    call["operation"] = "reference_to_video"
                    images = [start_url]
                    for reference in plan["characters"]:
                        face_number = len(images) + 1
                        images.extend(upload_image_fal(reference[key]) for key in ("frontal", "outfit"))
                        call["prompt"] += (f" @Image{face_number} is the approved identity for"
                                           f" {reference['character_id']}; @Image{face_number + 1}"
                                           " is that character's approved outfit.")
                    call["reference_image_urls"] = images
                    call["prompt"] += " @Image1 is the approved shot keyframe."
                paid_call_started = True
                result = provider_tool.execute(call)
                # Providers do not always report charges for failed queued
                # requests. Hold the estimate conservatively in that case.
                observed_cost = result.cost_usd if result.success or result.cost_usd else estimate
                tracker.reconcile(entry_id, observed_cost, success=result.success)
                return result
            except Exception:
                if paid_call_started:
                    tracker.reconcile(entry_id, estimate, success=False)
                else:
                    tracker.refund(entry_id)
                raise
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
