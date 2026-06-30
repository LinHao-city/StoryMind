"""Character Sheet — role-based visual consistency anchor system.

Maintains a registry of characters with their exact visual descriptions.
All video generation prompts that feature a character automatically
receive their full description injected, preventing visual drift
across independently generated shots.

Inspired by character consistency management in Jellyfish and Toonflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


@dataclass
class Character:
    name: str
    description: str           # Visual anchor: gender/age/ethnicity/hair/clothing/distinguishing features
    role: str = ""             # protagonist / antagonist / supporting
    reference_image: str = ""  # path to reference image (for InstantID Phase 3)
    voice_description: str = ""
    notes: str = ""            # director notes on how to portray


class CharacterSheet(BaseTool):
    """Manages a roster of characters and injects their descriptions into prompts.

    Usage:
        sheet = CharacterSheet()
        result = sheet.execute({
            "action": "add",
            "name": "Dr. Chen",
            "description": "Asian female scientist, 35, short black hair, white lab coat",
        })

        # Inject into prompt
        result = sheet.execute({
            "action": "inject",
            "prompt": "A scientist reads data on a holographic screen...",
            "characters_present": ["Dr. Chen"],
        })
    """

    name = "character_sheet"
    version = "1.0.0"
    tier = ToolTier.CORE
    capability = "planning"
    provider = "openmontage"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = []
    install_instructions = "No dependencies required."

    capabilities = ["character_consistency", "prompt_injection", "roster_management"]
    supports = {
        "reference_image": True,
        "multi_character": True,
        "prompt_injection": True,
        "json_export": True,
    }
    best_for = [
        "maintaining visual consistency of characters across multiple shots",
        "injecting character descriptions into video generation prompts",
        "managing cast for multi-scene productions",
    ]

    input_schema = {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "remove", "list", "inject", "save", "load"],
                "description": "Operation to perform",
            },
            "name": {"type": "string"},
            "description": {"type": "string"},
            "role": {"type": "string", "enum": ["protagonist", "antagonist", "supporting", ""]},
            "reference_image": {"type": "string"},
            "voice_description": {"type": "string"},
            "notes": {"type": "string"},
            "prompt": {"type": "string", "description": "Base prompt to inject characters into"},
            "characters_present": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of character names appearing in this shot",
            },
            "filepath": {"type": "string", "description": "Path to save/load character sheet JSON"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=1, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["action", "name"]
    side_effects = ["modifies in-memory character registry"]

    def __init__(self):
        self._roster: dict[str, Character] = {}

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def add(self, name: str, description: str, **kwargs) -> None:
        self._roster[name] = Character(name=name, description=description, **kwargs)

    def export(self) -> list[dict]:
        return [asdict(c) for c in self._roster.values()]

    def inject(self, prompt: str, characters_present: list[str]) -> str:
        """Append character descriptions to a prompt for all present characters."""
        anchors = []
        for char_name in characters_present:
            # Fuzzy match: support partial name
            matched = next(
                (c for k, c in self._roster.items()
                 if k.lower() == char_name.lower() or char_name.lower() in k.lower()),
                None,
            )
            if matched:
                anchors.append(
                    f"The character {matched.name} is: {matched.description}"
                )
        if anchors:
            injection = ". ".join(anchors)
            return f"{prompt.rstrip('.')}. {injection}."
        return prompt

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        action = inputs["action"]

        if action == "add":
            if not inputs.get("name") or not inputs.get("description"):
                return ToolResult(success=False, error="'name' and 'description' required for add")
            self.add(
                name=inputs["name"],
                description=inputs["description"],
                role=inputs.get("role", ""),
                reference_image=inputs.get("reference_image", ""),
                voice_description=inputs.get("voice_description", ""),
                notes=inputs.get("notes", ""),
            )
            return ToolResult(
                success=True,
                data={"added": inputs["name"], "roster_size": len(self._roster)},
            )

        elif action == "remove":
            removed = self._roster.pop(inputs.get("name", ""), None)
            return ToolResult(
                success=True,
                data={"removed": inputs.get("name"), "found": removed is not None},
            )

        elif action == "list":
            return ToolResult(
                success=True,
                data={"roster": self.export(), "count": len(self._roster)},
            )

        elif action == "inject":
            if not inputs.get("prompt"):
                return ToolResult(success=False, error="'prompt' required for inject")
            enhanced = self.inject(
                inputs["prompt"],
                inputs.get("characters_present", []),
            )
            return ToolResult(
                success=True,
                data={
                    "original_prompt": inputs["prompt"],
                    "enhanced_prompt": enhanced,
                    "characters_injected": inputs.get("characters_present", []),
                },
            )

        elif action == "save":
            path = Path(inputs.get("filepath", "character_sheet.json"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.export(), indent=2, ensure_ascii=False), encoding="utf-8")
            return ToolResult(success=True, data={"saved": str(path), "count": len(self._roster)})

        elif action == "load":
            path = Path(inputs.get("filepath", "character_sheet.json"))
            if not path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            self._roster = {}
            for c in data:
                self.add(**c)
            return ToolResult(success=True, data={"loaded": str(path), "count": len(self._roster)})

        return ToolResult(success=False, error=f"Unknown action: {action}")
