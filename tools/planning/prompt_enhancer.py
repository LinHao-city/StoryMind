"""Prompt Enhancer — converts plain descriptions into professional cinematography prompts.

Translates emotional adjectives ('epic', 'cinematic', 'dramatic') into their
visual causes, enforces shot-type vocabulary, and appends consistency anchors.

Implements the CHAI oversight loop pre/post-caption pass described in
OpenMontage's asset-director skill.
"""

from __future__ import annotations

import re
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

# Emotional adjective → visual cause translations
_EMOTION_TO_VISUAL = {
    "epic":        "extreme wide shot, low-angle, sweeping crane movement",
    "cinematic":   "anamorphic lens, shallow depth of field, motivated lighting",
    "dramatic":    "low-key lighting, deep shadows, slow dolly-in",
    "mysterious":  "fog/mist, backlit silhouette, cool desaturated palette",
    "tense":       "tight close-up, static shot, high contrast",
    "beautiful":   "golden hour, soft rim-lighting, rack focus",
    "dark":        "low-key, underexposed shadows, cold-blue tones",
    "emotional":   "extreme close-up on eyes, shallow DOF, soft lighting",
    "action":      "handheld camera, fast cuts, wide angle distortion",
    "peaceful":    "static wide shot, high-key, warm color temperature",
    "sad":         "overcast diffuse light, desaturated palette, slow pull-back",
    "hopeful":     "motivated window light, warm golden tones, tilt-up",
    "lonely":      "extreme wide establishing, subject small in frame, flat light",
    "threatening": "low-angle tilt-up on subject, harsh rim-light, deep shadows",
}

# Ambiguous / confusable cinematography terms
_CONFUSABLE_TERMS = {
    "zoom in":  "dolly-in (physical camera approach, not lens zoom)",
    "zoom out": "dolly-out (physical camera retreat)",
    "pan":      "horizontal pan (camera rotates on tripod axis)",
    "move":     "tracking shot or dolly",
    "aerial":   "aerial drone shot, bird's eye view",
    "fish eye": "fisheye lens, extreme barrel distortion",
}

# Shot scale keywords to inject proper technical terms
_SHOT_SCALE_MAP = {
    "extreme close": "ECU (extreme close-up)",
    "close up":      "CU (close-up)",
    "medium shot":   "MS (medium shot)",
    "wide shot":     "WS (wide shot)",
    "full body":     "LS (long shot), full body",
    "establishing":  "EWS (extreme wide shot), establishing",
}


class PromptEnhancer(BaseTool):
    """Enhances video/image generation prompts with professional cinematography language."""

    name = "prompt_enhancer"
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

    capabilities = ["prompt_enhancement", "cinematography_translation"]
    supports = {
        "emotion_to_visual": True,
        "shot_scale_normalization": True,
        "consistency_injection": True,
        "negative_prompt": True,
    }
    best_for = [
        "translating story beats into specific visual instructions",
        "ensuring AI video models receive unambiguous cinematography language",
        "standardizing prompt quality across all shots in a sequence",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string", "description": "Base prompt to enhance"},
            "shot_plan": {
                "type": "object",
                "description": "Single shot from StoryboardPlanner output to use as template",
            },
            "consistency_suffix": {
                "type": "string",
                "description": "Suffix from SceneConsistencyTracker to append",
            },
            "style_reference": {
                "type": "string",
                "description": "Film style reference: 'Blade Runner 2049', '2001 A Space Odyssey'",
            },
            "negative_prompt": {
                "type": "string",
                "description": "Base negative prompt to extend",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=32, vram_mb=0, disk_mb=0, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["prompt", "style_reference"]
    side_effects = []

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def _translate_emotions(self, text: str) -> str:
        result = text
        for emotion, visual in _EMOTION_TO_VISUAL.items():
            pattern = re.compile(rf"\b{emotion}\b", re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(f"{emotion} ({visual})", result, count=1)
        return result

    def _normalize_shot_scale(self, text: str) -> str:
        result = text
        for plain, technical in _SHOT_SCALE_MAP.items():
            pattern = re.compile(rf"\b{re.escape(plain)}\b", re.IGNORECASE)
            if pattern.search(result) and technical not in result:
                result = pattern.sub(technical, result, count=1)
        return result

    def _build_from_shot_plan(self, shot: dict) -> tuple[str, str]:
        """Build prompt + negative_prompt from a storyboard shot plan dict."""
        parts = []

        scale = shot.get("shot_scale", "")
        movement = shot.get("camera_movement", "")
        lighting = shot.get("lighting", "")
        action = shot.get("action", "")
        location = shot.get("location", "")
        chars = shot.get("characters_present", [])

        if scale:
            parts.append(f"{scale} shot")
        if location:
            parts.append(f"of {location}")
        if action:
            parts.append(action)
        if movement and movement != "static":
            parts.append(f"{movement} camera movement")
        if lighting:
            parts.append(lighting)

        base = shot.get("video_prompt") or ", ".join(parts)
        negative = shot.get("negative_prompt", "blurry, shaky, overexposed, cartoon, text, watermark, low quality")
        return base, negative

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        shot_plan = inputs.get("shot_plan")
        consistency = inputs.get("consistency_suffix", "")
        style_ref = inputs.get("style_reference", "")
        base_negative = inputs.get("negative_prompt", "blurry, shaky, cartoon, text, watermark, low quality")

        if shot_plan:
            prompt, negative = self._build_from_shot_plan(shot_plan)
        else:
            prompt = inputs["prompt"]
            negative = base_negative

        # Step 1: Translate emotional adjectives → visual causes
        enhanced = self._translate_emotions(prompt)

        # Step 2: Normalize shot scale terms
        enhanced = self._normalize_shot_scale(enhanced)

        # Step 3: Append style reference
        if style_ref:
            style_keywords = {
                "blade runner 2049":    "teal-and-orange palette, anamorphic flares, neon reflections in rain",
                "2001 a space odyssey": "cold clinical white, slow deliberate movement, vast silence",
                "interstellar":         "golden wheat fields to black void contrast, IMAX framing, orchestral scale",
                "arrival":              "desaturated blue-grey palette, wide establishing shots, slow push-ins",
                "dune":                 "warm amber desert tones, extreme wide establishing, shallow silhouettes",
            }
            style_key = style_ref.lower()
            for ref_name, keywords in style_keywords.items():
                if ref_name in style_key:
                    enhanced = f"{enhanced}, {keywords}"
                    break
            else:
                enhanced = f"{enhanced}, visual style inspired by {style_ref}"

        # Step 4: Append consistency anchors
        if consistency:
            enhanced = f"{enhanced.rstrip(', ')}, {consistency}"

        # Step 5: Always end with quality markers
        quality_tail = "cinematic 24fps, photorealistic, 4K detail, professional color grade"
        if "cinematic" not in enhanced.lower():
            enhanced = f"{enhanced}, {quality_tail}"

        return ToolResult(
            success=True,
            data={
                "original_prompt": inputs.get("prompt", ""),
                "enhanced_prompt": enhanced.strip(),
                "negative_prompt": negative,
                "changes_applied": [
                    k for k in _EMOTION_TO_VISUAL if k in inputs.get("prompt", "").lower()
                ],
            },
        )
