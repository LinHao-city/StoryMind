"""NetEase Leihuo Gateway image generation — Doubao SeeDream-5.0 and gpt-image-2."""

from __future__ import annotations

import base64
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


class LeihuoImage(BaseTool):
    name = "leihuo_image"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "image_generation"
    provider = "leihuo"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = "Set LEIHUO_API_KEY in .env."

    capabilities = ["generate_image", "text_to_image", "generate_illustration"]
    supports = {
        "complex_instructions": True,
        "text_in_image": True,
        "multiple_outputs": False,
    }
    best_for = [
        "Doubao SeeDream-5.0 high-quality image generation via NetEase gateway",
        "gpt-image-2 with detailed instruction-following",
        "image generation without needing OpenAI or fal.ai keys",
    ]
    not_good_for = ["offline generation", "image editing", "reference-conditioned generation"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "enum": ["doubao-seedream-5-0-260128", "gpt-image-2"],
                "default": "doubao-seedream-5-0-260128",
                "description": (
                    "doubao-seedream-5-0-260128: ByteDance Doubao SeeDream (recommended); "
                    "gpt-image-2: OpenAI GPT-Image-2 via Leihuo"
                ),
            },
            "size": {
                "type": "string",
                "default": "2048x2048",
                "description": (
                    "doubao-seedream-5-0-260128 requires >= 3,686,400 pixels "
                    "(e.g. 2048x2048, 2560x1440, 1920x1920). "
                    "gpt-image-2 accepts standard sizes (1024x1024, 1024x1792, 1792x1024)."
                ),
            },
            "quality": {
                "type": "string",
                "enum": ["low", "medium", "high", "standard", "hd"],
                "default": "high",
            },
            "n": {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=100, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "size", "quality"]
    side_effects = ["writes image file to output_path", "calls Leihuo gateway API"]
    user_visible_verification = ["Inspect generated image for relevance and quality"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("LEIHUO_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        model = inputs.get("model", "doubao-seedream-5-0-260128")
        n = inputs.get("n", 1)
        quality = inputs.get("quality", "high")
        if model == "gpt-image-2":
            cost_map = {"low": 0.011, "medium": 0.042, "high": 0.167, "standard": 0.04, "hd": 0.08}
            return cost_map.get(quality, 0.042) * n
        return round(0.02 * n, 4)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="LEIHUO_API_KEY not set. " + self.install_instructions,
            )

        from openai import OpenAI

        start = time.time()
        model = inputs.get("model", "doubao-seedream-5-0-260128")
        prompt = inputs["prompt"]
        size = inputs.get("size", "1024x1024")
        n = inputs.get("n", 1)
        quality = inputs.get("quality", "high")

        client = OpenAI(api_key=api_key, base_url=_BASE_URL)
        output_path = Path(inputs.get("output_path", "leihuo_image.png"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
                response_format="b64_json",
            )
            image_data = base64.b64decode(response.data[0].b64_json)
            output_path.write_bytes(image_data)
        except Exception as e:
            return ToolResult(success=False, error=f"Leihuo image generation failed: {e}")

        return ToolResult(
            success=True,
            data={
                "provider": "leihuo",
                "model": model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
