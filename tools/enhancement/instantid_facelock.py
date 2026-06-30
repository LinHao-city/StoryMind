"""InstantID Face Lock — post-processing character face consistency.

Phase 3 upgrade. Requires NVIDIA GPU with >= 16GB VRAM.

Reference: InstantX-Team/InstantID (github.com/InstantX-Team/InstantID)

Takes a reference portrait image and applies face-consistent regeneration
across all video clips in a sequence, ensuring the protagonist looks the
same in every shot regardless of which AI model generated each clip.

When GPU is unavailable, returns UNAVAILABLE status — the pipeline
falls back gracefully without breaking.

Installation:
    pip install -r requirements-gpu.txt
    # Download InstantID model weights:
    huggingface-cli download InstantX/InstantID --local-dir models/instantid
"""

from __future__ import annotations

import os
import shutil
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

_INSTANTID_MODEL_PATH = Path("models/instantid")
_MIN_VRAM_GB = 16


def _check_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory >= _MIN_VRAM_GB * 1024**3
    except ImportError:
        return False


def _check_instantid() -> bool:
    return _INSTANTID_MODEL_PATH.exists() and any(_INSTANTID_MODEL_PATH.iterdir())


class InstantIDFaceLock(BaseTool):
    """Post-processor: locks character face across all generated video clips.

    Status: PHASE 3 — requires GPU >= 16GB VRAM + InstantID model weights.
    When unavailable, returns UNAVAILABLE so the pipeline skips gracefully.
    """

    name = "instantid_facelock"
    version = "0.1.0"
    tier = ToolTier.ENHANCE
    capability = "enhancement"
    provider = "instantid"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.LOCAL_GPU

    dependencies = ["python:torch", "python:diffusers"]
    install_instructions = (
        "Phase 3 requirement — needs GPU >= 16GB VRAM.\n"
        "  1. pip install -r requirements-gpu.txt\n"
        "  2. huggingface-cli download InstantX/InstantID --local-dir models/instantid\n"
        "  Reference: https://github.com/InstantX-Team/InstantID"
    )

    capabilities = ["face_consistency", "character_lock", "identity_preservation"]
    supports = {
        "video_input": True,
        "batch_processing": True,
        "strength_control": True,
        "offline": True,
    }
    best_for = [
        "ensuring protagonist face is identical across all generated clips",
        "fixing face inconsistency introduced by independent per-shot generation",
        "production-grade character consistency in multi-shot sequences",
    ]
    not_good_for = [
        "systems without GPU",
        "real-time generation",
        "non-human subjects",
    ]

    input_schema = {
        "type": "object",
        "required": ["reference_image", "video_paths"],
        "properties": {
            "reference_image": {
                "type": "string",
                "description": "Path to clean portrait reference image of the character",
            },
            "video_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of video file paths to process",
            },
            "output_dir": {
                "type": "string",
                "description": "Directory for face-locked output videos",
            },
            "strength": {
                "type": "number",
                "default": 0.8,
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Face injection strength (0=no change, 1=full replacement)",
            },
            "preserve_expression": {
                "type": "boolean",
                "default": True,
                "description": "Keep original expression, change only identity features",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=4, ram_mb=8192, vram_mb=16384, disk_mb=5000, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["reference_image", "video_paths", "strength"]
    side_effects = ["writes face-locked videos to output_dir", "GPU inference"]
    user_visible_verification = [
        "Compare protagonist face in input vs output clips",
        "Verify expressions and actions are preserved",
    ]

    def get_status(self) -> ToolStatus:
        if not _check_gpu():
            return ToolStatus.UNAVAILABLE
        if not _check_instantid():
            return ToolStatus.UNAVAILABLE
        try:
            import torch
            import diffusers  # noqa: F401
            return ToolStatus.AVAILABLE
        except ImportError:
            return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0  # local GPU, no API cost

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        status = self.get_status()
        if status == ToolStatus.UNAVAILABLE:
            reasons = []
            if not _check_gpu():
                reasons.append(f"No NVIDIA GPU with >= {_MIN_VRAM_GB}GB VRAM detected")
            if not _check_instantid():
                reasons.append(f"InstantID model weights not found at {_INSTANTID_MODEL_PATH}")
            return ToolResult(
                success=False,
                error=(
                    "InstantID Face Lock is a Phase 3 feature requiring GPU setup.\n"
                    + "\n".join(f"  - {r}" for r in reasons)
                    + f"\n\nInstallation: {self.install_instructions}"
                ),
            )

        # GPU + InstantID available — run face lock
        # Full implementation requires:
        #   1. Extract frames from each video
        #   2. Run InstantID face injection on each frame
        #   3. Re-encode frames back to video
        # This scaffold will be completed when GPU environment is confirmed.
        return ToolResult(
            success=False,
            error=(
                "InstantID Face Lock GPU scaffold detected. "
                "Full frame-level implementation pending GPU environment confirmation. "
                "Contact project maintainer to complete Phase 3."
            ),
        )
