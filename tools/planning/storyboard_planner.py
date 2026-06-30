"""Storyboard Planner — LLM-powered cinematic shot decomposition.

Inspired by Jellyfish (github.com/Forget-C/Jellyfish) and Toonflow
(github.com/HBAI-Ltd/Toonflow-app).

Takes a script/treatment and outputs a structured shot plan with:
  - Shot type (ECU/CU/MS/WS/EWS/aerial)
  - Camera movement (static/dolly/pan/crane/handheld)
  - Lighting design (high-key/low-key/practical/etc.)
  - Emotional beat
  - Character positions
  - Professional video generation prompt
"""

from __future__ import annotations

import json
import os
import time
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

# Shot type definitions for the LLM prompt
_SHOT_VOCABULARY = """
SHOT SCALES:
- ECU (Extreme Close-Up): eyes, hands, single detail — maximum emotion/tension
- CU (Close-Up): face/head — reaction, emotion, intimacy
- MCU (Medium Close-Up): chest up — dialogue, relationship
- MS (Medium Shot): waist up — action, interaction
- MLS (Medium Long Shot): knees up — physical action
- LS (Long Shot): full body in environment — character placement
- WS (Wide Shot): character + significant surroundings — context
- EWS (Extreme Wide Shot): landscape, establishing — scale, isolation
- AERIAL: bird's eye, drone — god-view, consequence, transition

CAMERA MOVEMENTS:
- static: stability, observation, formality
- dolly-in: intensification, revelation, intimacy
- dolly-out / pull-back: isolation, scale reveal, consequence
- pan-left / pan-right: landscape reveal, following action
- tilt-up: power, awe, ascension
- tilt-down: vulnerability, descent, gravity
- tracking-shot: urgency, following character
- crane-up: god's view, climax, farewell
- handheld: urgency, chaos, documentary realism
- arc-shot: revealing environment around subject

LIGHTING:
- high-key: optimism, commercial, open
- low-key: drama, mystery, danger
- practical-lighting: intimacy, realism (lamp/screen/fire sources)
- motivated-window: natural daylight, hope
- golden-hour: warmth, nostalgia, beauty
- cold-blue: alienation, sadness, clinical, sci-fi
- neon-accent: cyberpunk, urban, modern
- backlit-silhouette: mystery, iconic, power
- rim-lighting: separation from background, cinematic depth
"""


class StoryboardPlanner(BaseTool):
    name = "storyboard_planner"
    version = "1.0.0"
    tier = ToolTier.CORE
    capability = "planning"
    provider = "leihuo"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = "Set LEIHUO_API_KEY in .env (used to call Claude for shot planning)."

    capabilities = ["storyboard_generation", "shot_planning", "cinematography"]
    supports = {
        "character_consistency": True,
        "shot_type_selection": True,
        "camera_movement": True,
        "lighting_design": True,
        "prompt_generation": True,
    }
    best_for = [
        "decomposing scripts into professional cinematic shot plans",
        "generating video prompts with proper shot language",
        "ensuring narrative pacing and emotional arc across scenes",
    ]

    input_schema = {
        "type": "object",
        "required": ["treatment"],
        "properties": {
            "treatment": {
                "type": "string",
                "description": "Script, treatment, or story description to decompose into shots",
            },
            "target_duration": {
                "type": "number",
                "default": 30,
                "description": "Target video duration in seconds",
            },
            "shot_count": {
                "type": "integer",
                "default": 6,
                "minimum": 2,
                "maximum": 20,
                "description": "Number of shots to plan",
            },
            "genre": {
                "type": "string",
                "default": "cinematic drama",
                "description": "Genre: sci-fi / drama / action / documentary / thriller / etc.",
            },
            "mood": {
                "type": "string",
                "default": "contemplative",
                "description": "Overall emotional tone of the piece",
            },
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
                "description": "Character roster with visual descriptions for consistency",
            },
            "style_reference": {
                "type": "string",
                "description": "Visual style reference: '2001 A Space Odyssey', 'Blade Runner 2049', etc.",
            },
            "model": {
                "type": "string",
                "default": "claude-haiku-4-5-20251001",
                "description": "LLM model for planning (claude-haiku-4-5-20251001 or claude-opus-4-6)",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=10, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["treatment", "shot_count", "genre", "mood"]
    side_effects = ["calls Leihuo LLM API"]
    user_visible_verification = [
        "Review shot plan for narrative coherence and pacing",
        "Verify character descriptions are injected consistently",
    ]

    def _get_api_key(self) -> str | None:
        return os.environ.get("LEIHUO_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = self._get_api_key()
        if not api_key:
            return ToolResult(
                success=False,
                error="LEIHUO_API_KEY not set. " + self.install_instructions,
            )

        from openai import OpenAI

        start = time.time()
        treatment = inputs["treatment"]
        shot_count = inputs.get("shot_count", 6)
        duration = inputs.get("target_duration", 30)
        genre = inputs.get("genre", "cinematic drama")
        mood = inputs.get("mood", "contemplative")
        style_ref = inputs.get("style_reference", "")
        characters = inputs.get("characters", [])
        model = inputs.get("model", "claude-haiku-4-5-20251001")

        # Build character roster block
        char_block = ""
        if characters:
            char_block = "\n\nCHARACTER ROSTER (must be described consistently in every shot they appear):\n"
            for c in characters:
                char_block += f"- {c['name']}: {c['description']}\n"

        style_block = f"\nVISUAL STYLE REFERENCE: {style_ref}" if style_ref else ""

        system_prompt = f"""You are a world-class cinematographer and film director.
You have deep knowledge of visual storytelling, shot composition, and cinematic language.
{_SHOT_VOCABULARY}

Your task: decompose a story treatment into a precise, professional shot plan.
Each shot must serve the narrative and emotional arc. Think like Christopher Nolan, Denis Villeneuve, or Roger Deakins."""

        user_prompt = f"""Decompose this treatment into exactly {shot_count} shots for a {duration}-second {genre} film.

TREATMENT:
{treatment}

OVERALL MOOD: {mood}{style_block}{char_block}

Return a JSON object with this exact structure:
{{
  "title": "film title",
  "logline": "one sentence description",
  "emotional_arc": "brief description of how emotion develops across shots",
  "total_duration": {duration},
  "shots": [
    {{
      "shot_number": 1,
      "shot_scale": "WS",
      "camera_movement": "dolly-in",
      "lighting": "cold-blue, rim-lighting",
      "location": "brief location description",
      "characters_present": ["name1"],
      "action": "what is happening in this shot",
      "emotional_beat": "what emotion this shot conveys",
      "duration_seconds": 6,
      "transition_to_next": "cut / dissolve / fade / match-cut",
      "video_prompt": "A [shot_scale] shot of [detailed visual description], [camera_movement] revealing [subject], [lighting], [mood adjectives translated to visual causes], cinematic 24fps, [style keywords], photorealistic",
      "negative_prompt": "blurry, shaky, overexposed, cartoon, text, watermark"
    }}
  ]
}}

RULES:
1. video_prompt must be in English, professional, specific — no vague adjectives like 'epic' or 'cinematic' without visual cause
2. Every shot featuring a character must include their full visual description in video_prompt
3. Shot durations must sum to {duration} seconds
4. The arc must have: establishing → rising tension → climax → resolution
5. No two consecutive shots should have the same shot scale
6. Return ONLY the JSON, no markdown fences"""

        try:
            # Claude models on Leihuo require Anthropic SDK (not OpenAI SDK)
            import anthropic

            anthropic_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or api_key
            anthropic_base = os.environ.get("ANTHROPIC_BASE_URL", "https://ai.leihuo.netease.com/")

            client = anthropic.Anthropic(
                api_key=anthropic_key,
                base_url=anthropic_base,
            )
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown fences if model added them
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            plan = json.loads(raw)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                error=f"LLM returned invalid JSON: {e}\nRaw: {raw[:300]}",
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Storyboard planning failed: {e}")

        shots = plan.get("shots", [])
        return ToolResult(
            success=True,
            data={
                "title": plan.get("title", "Untitled"),
                "logline": plan.get("logline", ""),
                "emotional_arc": plan.get("emotional_arc", ""),
                "total_duration": plan.get("total_duration", duration),
                "shot_count": len(shots),
                "shots": shots,
            },
            cost_usd=0.001 * len(user_prompt) / 1000,
            duration_seconds=round(time.time() - start, 2),
            model=model,
        )
