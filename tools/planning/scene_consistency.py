"""Scene Consistency Tracker — cross-shot visual anchor system.

Inspired by Jellyfish (github.com/Forget-C/Jellyfish) consistency management.

Tracks visual anchors extracted from the first generated shot and
propagates them as consistency constraints across all subsequent shots
in the same sequence. Prevents visual drift in color grade, lighting
style, environment details, and character appearance.

Key concepts:
  - Style anchor: color palette, grain, aspect ratio treatment
  - Environment anchor: recurring location details (sky color, props, set elements)
  - Character anchor: per-character clothing/hair/expression baseline
  - Negative anchor: elements that must NOT appear (breaks continuity)
"""

from __future__ import annotations

import json
import os
import time
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

_BASE_URL = "https://ai.leihuo.netease.com/v1"


class SceneConsistencyTracker(BaseTool):
    """Tracks and enforces visual consistency across shots.

    Usage:
        tracker = SceneConsistencyTracker()

        # After generating shot 1, register its style
        tracker.execute({"action": "register_anchor",
                         "shot_number": 1,
                         "prompt_used": "...",
                         "visual_description": "cold blue palette, dimly lit lab..."})

        # Before generating shot 3, get consistency modifiers
        result = tracker.execute({"action": "get_consistency_suffix",
                                  "base_prompt": "A scientist reads alien data..."})
        enhanced = result.data["enhanced_prompt"]
    """

    name = "scene_consistency_tracker"
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

    capabilities = [
        "visual_anchor_tracking",
        "consistency_enforcement",
        "style_propagation",
        "negative_prompt_management",
    ]
    supports = {
        "style_anchors": True,
        "character_anchors": True,
        "environment_anchors": True,
        "negative_anchors": True,
        "auto_extraction": True,
    }
    best_for = [
        "preventing visual drift across independently generated video clips",
        "maintaining color grade and lighting style across all shots",
        "enforcing character clothing/appearance consistency",
    ]

    input_schema = {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "register_anchor",
                    "add_style_anchor",
                    "add_negative_anchor",
                    "get_consistency_suffix",
                    "get_full_context",
                    "reset",
                    "save",
                    "load",
                ],
            },
            "shot_number": {"type": "integer"},
            "prompt_used": {"type": "string"},
            "visual_description": {"type": "string"},
            "anchor_type": {"type": "string", "enum": ["style", "environment", "character", "negative"]},
            "anchor_text": {"type": "string"},
            "base_prompt": {"type": "string"},
            "filepath": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=64, vram_mb=0, disk_mb=1, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["action", "shot_number"]
    side_effects = ["modifies in-memory anchor registry"]

    def __init__(self):
        self._style_anchors: list[str] = []
        self._environment_anchors: list[str] = []
        self._character_anchors: list[str] = []
        self._negative_anchors: list[str] = []
        self._shot_log: list[dict] = []

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def _build_consistency_suffix(self) -> str:
        """Build a suffix to append to any video prompt for consistency."""
        parts = []
        if self._style_anchors:
            parts.append(", ".join(self._style_anchors[:3]))
        if self._environment_anchors:
            parts.append(", ".join(self._environment_anchors[:2]))
        if self._character_anchors:
            parts.append(", ".join(self._character_anchors[:3]))
        return ", ".join(parts) if parts else ""

    def _build_negative_suffix(self) -> str:
        return ", ".join(self._negative_anchors) if self._negative_anchors else ""

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        action = inputs["action"]

        if action == "register_anchor":
            prompt = inputs.get("prompt_used", "")
            desc = inputs.get("visual_description", "")
            shot_num = inputs.get("shot_number", len(self._shot_log) + 1)

            # Extract style cues from the first shot to anchor the whole film
            if shot_num == 1 or not self._style_anchors:
                # Auto-extract key visual descriptors
                for keyword in [
                    "cold-blue", "warm-amber", "golden-hour", "neon", "desaturated",
                    "high-contrast", "low-key", "high-key", "anamorphic", "cinematic grain",
                    "teal-and-orange", "monochromatic",
                ]:
                    if keyword in (prompt + desc).lower():
                        self._style_anchors.append(keyword)

            self._shot_log.append({
                "shot": shot_num,
                "prompt": prompt[:200],
                "visual_description": desc[:200],
            })
            return ToolResult(
                success=True,
                data={
                    "registered": shot_num,
                    "style_anchors": self._style_anchors,
                    "total_shots_logged": len(self._shot_log),
                },
            )

        elif action == "add_style_anchor":
            text = inputs.get("anchor_text", "")
            if text and text not in self._style_anchors:
                self._style_anchors.append(text)
            return ToolResult(success=True, data={"style_anchors": self._style_anchors})

        elif action == "add_negative_anchor":
            text = inputs.get("anchor_text", "")
            if text and text not in self._negative_anchors:
                self._negative_anchors.append(text)
            return ToolResult(success=True, data={"negative_anchors": self._negative_anchors})

        elif action == "get_consistency_suffix":
            base = inputs.get("base_prompt", "")
            suffix = self._build_consistency_suffix()
            neg = self._build_negative_suffix()
            enhanced = f"{base.rstrip(', ')}{',' if base and suffix else ''} {suffix}".strip()
            return ToolResult(
                success=True,
                data={
                    "base_prompt": base,
                    "consistency_suffix": suffix,
                    "enhanced_prompt": enhanced,
                    "negative_prompt_additions": neg,
                },
            )

        elif action == "get_full_context":
            return ToolResult(
                success=True,
                data={
                    "style_anchors": self._style_anchors,
                    "environment_anchors": self._environment_anchors,
                    "character_anchors": self._character_anchors,
                    "negative_anchors": self._negative_anchors,
                    "shot_log": self._shot_log,
                },
            )

        elif action == "reset":
            self.__init__()
            return ToolResult(success=True, data={"reset": True})

        elif action == "save":
            path = Path(inputs.get("filepath", "consistency_tracker.json"))
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "style_anchors": self._style_anchors,
                "environment_anchors": self._environment_anchors,
                "character_anchors": self._character_anchors,
                "negative_anchors": self._negative_anchors,
                "shot_log": self._shot_log,
            }
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return ToolResult(success=True, data={"saved": str(path)})

        elif action == "load":
            path = Path(inputs.get("filepath", "consistency_tracker.json"))
            if not path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            self._style_anchors = data.get("style_anchors", [])
            self._environment_anchors = data.get("environment_anchors", [])
            self._character_anchors = data.get("character_anchors", [])
            self._negative_anchors = data.get("negative_anchors", [])
            self._shot_log = data.get("shot_log", [])
            return ToolResult(success=True, data={"loaded": str(path)})

        return ToolResult(success=False, error=f"Unknown action: {action}")
