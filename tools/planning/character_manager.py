"""File-backed character records and lock validation for character-film."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import ValidationError
from lib.character_film_state import FilmStateError, lock_character, validate_character_lock, validate_source_privacy
from schemas.artifacts import validate_artifact
from tools.base_tool import BaseTool, Determinism, ExecutionMode, ResourceProfile, RetryPolicy, ToolResult, ToolRuntime, ToolStability, ToolStatus, ToolTier


class CharacterManager(BaseTool):
    name = "character_manager"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "planning"
    provider = "StoryMind"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    dependencies = []
    install_instructions = "No dependencies required."
    capabilities = ["character_records", "character_lock", "source_privacy"]
    supports = {"identity_outfit_separation": True, "private_source_defaults": True}
    input_schema = {
        "type": "object", "required": ["action", "project_dir"],
        "properties": {
            "action": {"enum": ["draft", "validate_lock", "lock", "save", "load"]},
            "project_dir": {"type": "string"},
            "character": {"type": "object"},
            "character_id": {"type": "string"},
            "approved_by": {"type": "string"},
            "id": {"type": "string"},
            "role": {"type": "string"},
            "age_category": {"type": "string"},
            "source_type": {"type": "string"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=1)
    retry_policy = RetryPolicy(max_retries=0)
    side_effects = ["save writes a character JSON file inside the project"]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    @staticmethod
    def draft(character_id: str, role: str, age_category: str = "unspecified", source_type: str = "description") -> dict[str, Any]:
        private = source_type == "private_family_photo"
        return {
            "id": character_id,
            "role": role,
            "age_category": age_category,
            "visual_importance": "principal",
            "dialogue_required": False,
            "scene_count": 0,
            "required_state_changes": [],
            "source": {
                "type": source_type,
                "privacy_classification": "FAMILY_PRIVATE" if private else "PRIVATE" if source_type == "other_photo" else "PUBLIC",
                "source_photos_local_only": private,
                "remote_character_creation_allowed": False,
                "downstream_use_original_photos": False,
            },
            "fictionalization_level": 3,
            "identity": {},
            "outfits": {},
            "required_outfits": [],
            "status": "DRAFT",
            "identity_locked": False,
        }

    @staticmethod
    def _character_path(project_dir: Path, character_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", character_id):
            raise FilmStateError("Character ID must use lowercase kebab-case")
        root = project_dir.resolve()
        path = (root / "characters" / character_id / "character.json").resolve()
        if not path.is_relative_to(root):
            raise FilmStateError("Character path must remain inside the project")
        return path

    @staticmethod
    def _validate_record(character: dict[str, Any]) -> None:
        validate_artifact("character_bible", {
            "version": "1.0", "story_fingerprint": "0" * 64,
            "characters": [character],
        })
        validate_source_privacy(character)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        action = inputs["action"]
        project_dir = Path(inputs["project_dir"])
        try:
            if action == "draft":
                character = self.draft(inputs["id"], inputs["role"], inputs.get("age_category", "unspecified"), inputs.get("source_type", "description"))
                self._validate_record(character)
                return ToolResult(success=True, data={"character": character})
            if action == "load":
                path = self._character_path(project_dir, inputs["character_id"])
                character = json.loads(path.read_text(encoding="utf-8"))
                self._validate_record(character)
                return ToolResult(success=True, data={"character": character, "path": str(path)})
            character = inputs["character"]
            if action == "validate_lock":
                validate_character_lock(character, project_dir)
                return ToolResult(success=True, data={"locked": True, "character_id": character["id"]})
            if action == "lock":
                locked = lock_character(character, project_dir, inputs.get("approved_by", ""))
                return ToolResult(success=True, data={"character": locked})
            if action == "save":
                self._validate_record(character)
                path = self._character_path(project_dir, character["id"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(character, indent=2, ensure_ascii=False), encoding="utf-8")
                return ToolResult(success=True, data={"path": str(path)}, artifacts=[str(path)])
        except (KeyError, OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=False, error=f"Unknown action: {action}")
