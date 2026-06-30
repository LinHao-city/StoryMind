"""NetEase Leihuo Gateway TTS — Mimo (free) and MiniMax Speech models.

Mimo model (mimo-v2.5-tts-voicedesign) is free ($0.00/M).
MiniMax speech models (speech-2.8-hd, speech-2.6-hd) are paid.
"""

from __future__ import annotations

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
_FREE_MODEL = "mimo-v2.5-tts-voicedesign"


class LeihuoTTS(BaseTool):
    name = "leihuo_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "leihuo"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set LEIHUO_API_KEY in .env.\n"
        "  Get a key from https://ai.leihuo.netease.com/"
    )
    fallback = "piper_tts"
    fallback_tools = ["piper_tts"]

    capabilities = ["text_to_speech", "voice_selection", "multilingual"]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "free_tier": True,
    }
    best_for = [
        "free Chinese and multilingual TTS via Mimo model",
        "cost-free narration on the Leihuo gateway",
        "high-quality MiniMax speech when budget allows",
    ]
    not_good_for = ["offline generation", "voice cloning"]

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "model": {
                "type": "string",
                "enum": [
                    "mimo-v2.5-tts-voicedesign",
                    "speech-2.8-hd",
                    "speech-2.6-hd",
                ],
                "default": "mimo-v2.5-tts-voicedesign",
                "description": "mimo-v2.5-tts-voicedesign is FREE; speech-2.8-hd / speech-2.6-hd are MiniMax paid models",
            },
            "voice": {
                "type": "string",
                "default": "alloy",
                "description": "Voice name (model-dependent; Mimo supports custom voice design via prompt)",
            },
            "format": {
                "type": "string",
                "default": "mp3",
                "enum": ["mp3", "wav", "pcm"],
            },
            "speed": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0,
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["text", "voice", "model", "format", "speed"]
    side_effects = ["writes audio file to output_path", "calls Leihuo gateway API"]
    user_visible_verification = ["Listen to generated audio for intelligibility and tone"]

    def _get_api_key(self) -> str | None:
        return os.environ.get("LEIHUO_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        model = inputs.get("model", _FREE_MODEL)
        if model == _FREE_MODEL:
            return 0.0
        # MiniMax speech-2.8-hd: $47.945/M characters
        return round(len(inputs.get("text", "")) / 1_000_000 * 47.945, 6)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="LEIHUO_API_KEY not set. " + self.install_instructions,
            )

        from openai import OpenAI

        from tools.analysis.audio_probe import probe_duration

        start = time.time()
        model = inputs.get("model", _FREE_MODEL)
        voice = inputs.get("voice", "alloy")
        fmt = inputs.get("format", "mp3")
        text = inputs["text"]

        client = OpenAI(api_key=api_key, base_url=_BASE_URL)
        output_path = Path(inputs.get("output_path", f"leihuo_tts.{fmt}"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with client.audio.speech.with_streaming_response.create(
                model=model,
                voice=voice,
                input=text,
                response_format=fmt,
                speed=inputs.get("speed", 1.0),
            ) as resp:
                resp.stream_to_file(output_path)
        except Exception as e:
            return ToolResult(success=False, error=f"Leihuo TTS failed: {e}")

        audio_duration = probe_duration(output_path)
        return ToolResult(
            success=True,
            data={
                "provider": "leihuo",
                "model": model,
                "voice": voice,
                "format": fmt,
                "text_length": len(text),
                "audio_duration_seconds": round(audio_duration, 2) if audio_duration else None,
                "output": str(output_path),
            },
            artifacts=[str(output_path)],
            cost_usd=self.estimate_cost(inputs),
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
