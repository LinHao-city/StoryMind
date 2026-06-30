"""NetEase Leihuo Gateway video generation — Doubao Seedance 2.0.

Uses the OpenAI-compatible /v1/videos/generations task-based endpoint pattern
that most Chinese AI gateways expose for video models.

If the gateway returns a different format, adjust _submit and _poll accordingly.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

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
_DEFAULT_MODEL = "doubao-seedance-2-0-260128"
_POLL_INTERVAL = 5
_MAX_WAIT_SECONDS = 600


class LeihuoVideo(BaseTool):
    name = "leihuo_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "leihuo"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = "Set LEIHUO_API_KEY in .env."
    fallback_tools = ["seedance_video", "kling_video"]

    capabilities = ["text_to_video", "image_to_video"]
    supports = {
        "text_to_video": True,
        "image_to_video": True,
        "native_audio": True,
        "cinematic_quality": True,
        "aspect_ratio": True,
        "seed": True,
    }
    best_for = [
        "Doubao Seedance 2.0 cinematic video generation via NetEase Leihuo gateway",
        "video generation without fal.ai or Runway keys",
        "Chinese-market video generation with native audio",
    ]
    not_good_for = ["offline generation", "multi-reference video generation"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "model": {
                "type": "string",
                "enum": ["doubao-seedance-2-0-260128"],
                "default": "doubao-seedance-2-0-260128",
            },
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video"],
                "default": "text_to_video",
            },
            "duration": {
                "type": "string",
                "enum": ["4", "5", "6", "7", "8", "10"],
                "default": "5",
                "description": "Duration in seconds",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                "default": "16:9",
            },
            "resolution": {
                "type": "string",
                "enum": ["480p", "720p"],
                "default": "720p",
            },
            "generate_audio": {
                "type": "boolean",
                "default": True,
            },
            "image_url": {
                "type": "string",
                "description": "Start frame image URL for image_to_video",
            },
            "seed": {"type": "integer"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "model", "operation", "duration", "seed"]
    side_effects = ["writes video file to output_path", "calls Leihuo gateway API"]
    user_visible_verification = [
        "Watch generated clip for motion coherence, audio sync, and visual quality"
    ]

    def _get_api_key(self) -> str | None:
        return os.environ.get("LEIHUO_API_KEY")

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        duration = int(inputs.get("duration", "5"))
        # Approximate cost for Doubao Seedance via gateway
        return round(0.25 * duration, 2)

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        return 120.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="LEIHUO_API_KEY not set. " + self.install_instructions,
            )

        start = time.time()
        model = inputs.get("model", _DEFAULT_MODEL)
        operation = inputs.get("operation", "text_to_video")

        payload: dict[str, Any] = {
            "model": model,
            "prompt": inputs["prompt"],
            "duration": inputs.get("duration", "5"),
            "aspect_ratio": inputs.get("aspect_ratio", "16:9"),
            "resolution": inputs.get("resolution", "720p"),
            "generate_audio": inputs.get("generate_audio", True),
        }
        if inputs.get("seed") is not None:
            payload["seed"] = inputs["seed"]
        if operation == "image_to_video" and inputs.get("image_url"):
            payload["image_url"] = inputs["image_url"]

        headers = self._headers(api_key)

        try:
            # Submit generation task
            submit_resp = requests.post(
                f"{_BASE_URL}/video/generations",
                headers=headers,
                json=payload,
                timeout=30,
            )
            submit_resp.raise_for_status()
            task_data = submit_resp.json()

            # Determine task ID — gateways vary in field name
            task_id = (
                task_data.get("id")
                or task_data.get("task_id")
                or task_data.get("request_id")
            )

            # If result URL already present (synchronous gateway), skip polling
            video_url = self._extract_video_url(task_data)
            if not video_url and task_id:
                video_url = self._poll(task_id, headers)

            if not video_url:
                return ToolResult(
                    success=False,
                    error=f"Leihuo video: no video URL in response. Full response: {task_data}",
                )

            # Download video
            video_resp = requests.get(video_url, timeout=120)
            video_resp.raise_for_status()

        except requests.HTTPError as e:
            body = ""
            try:
                body = e.response.text[:500]
            except Exception:
                pass
            return ToolResult(
                success=False,
                error=f"Leihuo video HTTP {e.response.status_code}: {body}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Leihuo video generation failed: {e}")

        output_path = Path(inputs.get("output_path", "leihuo_video.mp4"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(video_resp.content)

        try:
            from tools.video._shared import probe_output
            probed = probe_output(output_path)
        except Exception:
            probed = {}

        return ToolResult(
            success=True,
            data={
                "provider": "leihuo",
                "model": model,
                "prompt": inputs["prompt"],
                "operation": operation,
                "aspect_ratio": inputs.get("aspect_ratio", "16:9"),
                "resolution": inputs.get("resolution", "720p"),
                "output": str(output_path),
                "output_path": str(output_path),
                "format": "mp4",
                **probed,
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )

    def _extract_video_url(self, data: dict) -> str | None:
        """Try common response shapes for a completed video URL.

        Leihuo gateway wraps results in a 'data' envelope:
          {"code": "success", "data": {"status": "SUCCESS", "result_url": "https://..."}}
        """
        # Primary Leihuo shape
        inner = data.get("data") or {}
        if isinstance(inner, dict):
            url = inner.get("result_url") or inner.get("url") or inner.get("video_url")
            if url:
                return url

        # Fallback shapes
        output = data.get("output") or data.get("result") or {}
        if isinstance(output, dict):
            url = output.get("url") or output.get("video_url")
            if url:
                return url
        video = data.get("video") or {}
        if isinstance(video, dict):
            url = video.get("url")
            if url:
                return url
        return data.get("url") or data.get("video_url")

    def _poll(self, task_id: str, headers: dict[str, str]) -> str | None:
        """Poll task status until complete or timeout."""
        deadline = time.time() + _MAX_WAIT_SECONDS
        while time.time() < deadline:
            time.sleep(_POLL_INTERVAL)
            resp = requests.get(
                f"{_BASE_URL}/video/generations/{task_id}",
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            # Leihuo wraps status inside data envelope
            inner = data.get("data") or {}
            status = (
                inner.get("status")
                or data.get("status")
                or data.get("state")
                or ""
            ).upper()

            if status in ("SUCCEEDED", "COMPLETED", "DONE", "SUCCESS"):
                return self._extract_video_url(data)
            if status in ("FAILED", "CANCELLED", "ERROR", "FAIL"):
                raise RuntimeError(
                    f"Leihuo video task {task_id} ended with status {status}: "
                    + str(inner.get("fail_reason") or data.get("error") or "")
                )
        raise TimeoutError(
            f"Leihuo video task {task_id} did not complete within {_MAX_WAIT_SECONDS}s"
        )
