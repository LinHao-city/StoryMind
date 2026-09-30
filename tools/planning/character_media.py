"""Local source-photo intake and generated-image registration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.character_media import intake_source_photo, register_generated_image, validate_remote_source_use
from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode, ResourceProfile, RetryPolicy,
    ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier,
)


class CharacterMedia(BaseTool):
    name = "character_media"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "planning"
    provider = "StoryMind"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    dependencies = ["python:PIL"]
    install_instructions = "Install Pillow from requirements.txt."
    capabilities = ["source_photo_intake", "generated_image_registration"]
    supports = {"agent_native_output_registration": True, "network_upload": False}
    input_schema = {
        "type": "object", "required": ["action", "character"],
        "properties": {
            "action": {"enum": ["intake_source", "register_generated", "check_remote_source"]},
            "project_dir": {"type": "string"}, "character": {"type": "object"},
            "input_path": {"type": "string"},
            "category": {"enum": ["candidate", "identity", "outfit", "keyframe"]},
            "asset_id": {"type": "string"}, "provider": {"type": "string"},
            "model": {"type": "string"}, "prompt": {"type": "string"},
            "seed": {"type": ["integer", "null"]},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=256, disk_mb=100)
    retry_policy = RetryPolicy(max_retries=0)
    side_effects = ["copies an image into the project; no network call"]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            character = inputs["character"]
            if inputs["action"] == "check_remote_source":
                validate_remote_source_use(character, inputs["provider"])
                return ToolResult(success=True, data={"approved_provider": inputs["provider"]})
            project_dir = Path(inputs["project_dir"])
            input_path = Path(inputs["input_path"])
            if inputs["action"] == "intake_source":
                record = intake_source_photo(project_dir, character, input_path)
            elif inputs["action"] == "register_generated":
                record = register_generated_image(
                    project_dir, character, input_path,
                    category=inputs["category"], asset_id=inputs["asset_id"],
                    provider=inputs["provider"], model=inputs["model"],
                    prompt=inputs["prompt"], seed=inputs.get("seed"),
                )
            else:
                return ToolResult(success=False, error="Unknown character media action")
            return ToolResult(success=True, data={"asset": record}, artifacts=[str(project_dir / record["path"])])
        except (KeyError, OSError, ValueError) as exc:
            return ToolResult(success=False, error=str(exc))
