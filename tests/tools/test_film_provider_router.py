"""Character-film reference routing never accepts originals or silent swaps."""

import hashlib
import shutil
import subprocess

import pytest
from PIL import Image

from lib.character_film_state import artifact_fingerprint, lock_character, lock_story, story_fingerprint
from lib.film_continuity import validate_clips
from lib.film_delivery import validate_film_edit, validate_film_render, validate_film_final_review
from lib.checkpoint import get_completed_stages, get_next_stage, write_checkpoint, CheckpointValidationError
from tools.planning.character_manager import CharacterManager
from tools.video.film_provider_router import FilmProviderRouter
from tools.video.kling_video import KlingVideo
from tools.video.seedance_video import SeedanceVideo
from tools.video.video_compose import VideoCompose
from tools.analysis.visual_qa import VisualQA
from tools.video._shared import probe_output
from tools.base_tool import ToolResult, ToolStatus


def _inputs(tmp_path):
    project = tmp_path / "projects" / "project"
    refs = project / "characters" / "hero"
    refs.mkdir(parents=True)
    for name in ("master.png", "body.png", "coat.png"):
        Image.new("RGB", (16, 16), "blue").save(refs / name)
    story = {
        "version": "1.0", "revision": 1, "title": "A Short Film", "premise": "A light appears",
        "synopsis": "A hero sees a light", "narrative": {"beginning": "Light appears",
        "escalation": "It brightens", "climax": "Hero touches it", "resolution": "It fades"},
        "genre": "fantasy", "tone": "warm", "target_duration_seconds": 5,
        "characters": ["hero"], "locations": ["room"],
        "scenes": [{"id": "scene-1"}], "status": "AWAITING_APPROVAL",
    }
    story = lock_story(story, "user")
    hero = CharacterManager.draft("hero", "lead", "minor", "private_family_photo")
    hero["identity"] = {"master": "characters/hero/master.png",
                        "full_body": "characters/hero/body.png"}
    hero["outfits"] = {"coat": {"reference": "characters/hero/coat.png", "locked": True}}
    hero["required_outfits"] = ["coat"]
    hero["selected_candidate_id"] = "candidate-1"
    hero["status"] = "AWAITING_APPROVAL"
    hero = lock_character(hero, project, "user")
    bible = {"version": "1.0", "story_fingerprint": story_fingerprint(story),
             "characters": [hero]}
    plan = {"version": "1.0", "story_fingerprint": story_fingerprint(story),
            "shots": [{"id": "shot-1", "scene_id": "scene-1", "duration_seconds": 5,
                       "location": "room", "description": "Hero sees light", "camera": "dolly in",
                       "lighting": "warm", "video_prompt": "Hero sees a light",
                       "characters": [{"id": "hero", "outfit_id": "coat",
                                       "state": "dry", "position": "center"}]}]}
    keyframe_path = project / "assets" / "keyframes" / "shot-1.png"
    keyframe_path.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), "yellow").save(keyframe_path)
    review = {"verdict": "pass", "reviewer": "test", "notes": "fixture"}
    keyframes = {"version": "1.0", "shot_plan_fingerprint": artifact_fingerprint(plan),
                 "frames": [{"shot_id": "shot-1", "path": "assets/keyframes/shot-1.png",
                             "sha256": hashlib.sha256(keyframe_path.read_bytes()).hexdigest(),
                             "provider": "fixture", "model": "fixture", "prompt": "fixture",
                             "continuity_review": review, "creative_review": review}]}
    policy = {"approved_provider": "kling", "approved_by": "user",
              "model_variant": "v3/standard", "max_call_cost_usd": 1.0,
              "budget_usd": 10.0}
    proposal = {"version": "1.0", "story_fingerprint": story_fingerprint(story),
                "renderer_family": "cinematic-trailer", "render_runtime": "ffmpeg",
                "composition_mode": "templated",
                "options_considered": ["ffmpeg", "remotion", "hyperframes"],
                "approved_by": "user", "approved_at": "2026-09-29T00:00:00Z",
                "budget_usd": 10.0, "provider_policy": policy}
    return {"operation": "plan", "project_dir": str(project), "story_bible": story,
            "character_bible": bible, "film_shot_plan": plan, "film_keyframes": keyframes,
            "film_proposal": proposal,
            "shot_id": "shot-1", "provider": "kling", "model_variant": "v3/standard",
            "provider_policy": policy}


def test_router_privacy_and_no_source_photo(tmp_path):
    inputs = _inputs(tmp_path)
    router = FilmProviderRouter()
    blocked = router.execute(inputs)
    assert not blocked.success and "accessible output URL" in blocked.error
    inputs["provider_policy"]["public_output_approval"] = {
        "approved_by": "user", "provider": "kling",
    }
    planned = router.execute(inputs)
    assert planned.success
    refs = planned.data["plan"]["characters"]
    assert len(refs) == 1
    assert all("source" not in path for path in refs[0].values() if isinstance(path, str))
    inputs["model_variant"] = "v2.1/pro"
    assert not router.execute(inputs).success
    inputs["model_variant"] = "v3/standard"
    inputs["provider_policy"] = dict(inputs["provider_policy"])
    inputs["provider_policy"]["max_call_cost_usd"] = 2.0
    assert "proposal" in router.execute(inputs).error


def test_kling_v3_payload_uses_start_image_and_elements():
    payload = KlingVideo.build_payload({
        "prompt": "A hero turns", "operation": "image_to_video",
        "model_variant": "v3/standard", "duration": "5",
        "start_image_url": "https://example.test/start.png",
        "elements": [{"frontal_image_url": "https://example.test/master.png",
                      "reference_image_urls": ["https://example.test/body.png"]}],
    })
    assert payload["start_image_url"] == "https://example.test/start.png"
    assert "image_url" not in payload
    assert len(payload["elements"]) == 1
    assert KlingVideo().estimate_cost({"model_variant": "v3/standard", "duration": "10",
                                      "generate_audio": False}) == 0.84
    assert KlingVideo().estimate_cost({"model_variant": "v3/standard", "duration": "10",
                                      "generate_audio": True}) == 1.26


def test_seedance_reference_payload_uses_documented_api_fields():
    payload = SeedanceVideo.build_reference_payload({
        "reference_image_urls": ["https://example.test/identity.png"],
        "reference_video_urls": ["https://example.test/motion.mp4"],
        "reference_audio_urls": ["https://example.test/audio.wav"],
    })
    assert set(payload) == {"image_urls", "video_urls", "audio_urls"}
    assert payload["image_urls"] == ["https://example.test/identity.png"]
    with pytest.raises(ValueError, match="at most 9"):
        SeedanceVideo.build_reference_payload({
            "reference_image_urls": [f"https://example.test/{i}.png" for i in range(10)],
        })


def test_provider_menu_keeps_policy_rejection_blocked():
    options = FilmProviderRouter().execute({"operation": "rank", "requirements": {
        "duration_seconds": 5, "private_characters": True,
        "policy_rejected_providers": ["seedance"], "max_call_cost_usd": 10,
    }})
    assert options.success
    seedance = next(item for item in options.data["options"] if item["provider"] == "seedance")
    assert not seedance["eligible"]
    assert any("policy rejection" in reason for reason in seedance["reasons"])


def test_generate_reserves_budget_and_uploads_only_after_privacy_gate(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    inputs["operation"] = "generate"
    uploads = []
    calls = []
    monkeypatch.setattr("tools.video._shared.upload_image_fal",
                        lambda path: uploads.append(path) or f"https://example.test/{len(uploads)}.png")
    monkeypatch.setattr(KlingVideo, "get_status", lambda self: ToolStatus.AVAILABLE)
    monkeypatch.setattr(KlingVideo, "estimate_cost", lambda self, call: 0.4)
    monkeypatch.setattr(KlingVideo, "execute", lambda self, call:
                        calls.append(call) or ToolResult(success=True, cost_usd=0.35))
    router = FilmProviderRouter()
    blocked = router.execute(inputs)
    assert not blocked.success
    assert uploads == [] and calls == []
    inputs["provider_policy"]["public_output_approval"] = {
        "approved_by": "user", "provider": "kling",
    }
    result = router.execute(inputs)
    assert result.success, result.error
    assert len(uploads) == 4
    assert len(calls) == 1
    assert calls[0]["start_image_url"].startswith("https://example.test/")
    assert len(calls[0]["elements"]) == 1
    cost_log = tmp_path / "projects" / "project" / "artifacts" / "film_cost_log.json"
    assert cost_log.is_file()


def test_seedance_comparison_locks_landscape_720p(tmp_path, monkeypatch):
    inputs = _inputs(tmp_path)
    policy = inputs["provider_policy"]
    policy.update({"approved_provider": "seedance", "model_variant": "standard",
                   "public_output_approval": {"approved_by": "user", "provider": "seedance"}})
    inputs.update({"provider": "seedance", "model_variant": "standard"})
    plan = FilmProviderRouter().execute(inputs)
    assert plan.success, plan.error
    assert plan.data["plan"]["aspect_ratio"] == "16:9"
    assert plan.data["plan"]["resolution"] == "720p"

    calls = []
    monkeypatch.setattr("tools.video._shared.upload_image_fal",
                        lambda path: "https://example.test/reference.png")
    monkeypatch.setattr(SeedanceVideo, "get_status", lambda self: ToolStatus.AVAILABLE)
    monkeypatch.setattr(SeedanceVideo, "estimate_cost", lambda self, call: 0.4)
    monkeypatch.setattr(SeedanceVideo, "execute", lambda self, call:
                        calls.append(call) or ToolResult(success=True, cost_usd=0.4))
    result = FilmProviderRouter().execute(dict(inputs, operation="generate"))
    assert result.success, result.error
    assert calls[0]["operation"] == "reference_to_video"
    assert calls[0]["aspect_ratio"] == "16:9"
    assert calls[0]["resolution"] == "720p"
    assert len(calls[0]["reference_image_urls"]) == 3


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg required")
def test_approved_clip_can_be_composed_with_existing_runtime(tmp_path):
    inputs = _inputs(tmp_path)
    project = tmp_path / "projects" / "project"
    video = project / "assets" / "video" / "shot-1.mp4"
    video.parent.mkdir(parents=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=24:d=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
    ], check=True, capture_output=True, timeout=30)
    qa = VisualQA().execute({"operation": "review", "input_path": str(video),
                             "timestamps": [0.5, 2.5, 4.5]})
    assert qa.success and qa.data["frame_count"] == 3
    review = {"verdict": "pass", "reviewer": "fixture", "notes": "synthetic clip"}
    clips = {"version": "1.0",
             "shot_plan_fingerprint": artifact_fingerprint(inputs["film_shot_plan"]),
             "keyframes_fingerprint": artifact_fingerprint(inputs["film_keyframes"]),
             "clips": [{"shot_id": "shot-1", "path": "assets/video/shot-1.mp4",
                        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                        "provider": "fixture", "model": "fixture", "attempt_count": 1,
                        "cost_usd": 0, "sample_frames": [
                            str(path.relative_to(project)).replace("\\", "/")
                            for path in (project / "assets" / "video" / "review_frames").glob("*.jpg")
                        ], "continuity_review": review, "creative_review": review}]}
    validate_clips(clips, inputs["film_shot_plan"], inputs["film_keyframes"], project)
    proposal = inputs["film_proposal"]
    decisions = {"version": "1.0", "cuts": [{"id": "cut-1", "source": "shot-1",
                                              "in_seconds": 0, "out_seconds": 5}],
                 "renderer_family": "cinematic-trailer", "render_runtime": "ffmpeg",
                 "composition_mode": "templated"}
    assets = {"version": "1.0", "assets": [{"id": "shot-1", "type": "video",
                                                  "path": str(video), "source_tool": "fixture",
                                                  "scene_id": "scene-1"}]}
    validate_film_edit(decisions, assets, clips, proposal, project)
    output = project / "renders" / "final.mp4"
    rendered = VideoCompose().execute({"operation": "render", "edit_decisions": decisions,
                                        "asset_manifest": assets, "output_path": str(output),
                                        "proposal_packet": {"production_plan": {"render_runtime": "ffmpeg"}}})
    assert rendered.success, rendered.error
    probe = probe_output(output)
    report = {"version": "1.0", "outputs": [{"path": "renders/final.mp4",
                                                "format": "mp4", "resolution": "64x64",
                                                "duration_seconds": probe["duration_seconds"]}],
              "metadata": {"render_runtime": "ffmpeg"}}
    validate_film_render(report, proposal, project)
    final_review = {"version": "1.0", "output_path": "renders/final.mp4", "status": "pass",
                    "checks": {"technical_probe": {"valid_container": True},
                               "visual_spotcheck": {"frames_sampled": 4},
                               "audio_spotcheck": {"unexpected_silence": False},
                               "promise_preservation": {"render_runtime_used": "ffmpeg"},
                               "subtitle_check": {"subtitles_expected": False}},
                    "metadata": {"character_continuity_passed": True,
                                 "wardrobe_continuity_passed": True}}
    validate_film_final_review(final_review, report, proposal, project)
    final_review["metadata"]["character_continuity_passed"] = False
    with pytest.raises(ValueError, match="continuity"):
        validate_film_final_review(final_review, report, proposal, project)

    # Exercise the real checkpoint chain through delivery, then prove media
    # mutation invalidates the final stages on resume.
    final_review["metadata"]["character_continuity_passed"] = True
    pipeline_dir = tmp_path / "pipelines"
    project_id = "project"
    story = inputs["story_bible"]
    bible = inputs["character_bible"]
    candidate_path = project / "characters" / "hero" / "candidate" / "candidate-1.png"
    candidate_path.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), "green").save(candidate_path)
    candidates = {"version": "1.0", "story_fingerprint": story_fingerprint(story),
                  "selections": [{"character_id": "hero", "trait_profile": "Young hero",
                                  "fictionalization_level": 3,
                                  "candidates": [{"id": "candidate-1", "asset": {
                                      "path": "characters/hero/candidate/candidate-1.png",
                                      "sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
                                      "origin": "generated", "provider": "fixture", "model": "fixture",
                                      "prompt": "fixture"}}],
                                  "selected_candidate_id": "candidate-1",
                                  "approval": {"approved_by": "user",
                                               "approved_at": "2026-09-29T00:00:00Z"}}]}
    for stage, stage_artifacts in (
        ("story_development", {"story_bible": story}),
        ("character_discovery", {"character_bible": bible}),
        ("character_distillation", {"character_candidates": candidates}),
        ("character_lock", {"character_bible": bible}),
        ("proposal", {"film_proposal": proposal}),
        ("shot_planning", {"film_shot_plan": inputs["film_shot_plan"]}),
        ("keyframe_generation", {"film_keyframes": inputs["film_keyframes"]}),
        ("video_generation", {"film_clips": clips}),
    ):
        write_checkpoint(pipeline_dir, project_id, stage, "completed", stage_artifacts,
                         pipeline_type="character-film")
    with pytest.raises(CheckpointValidationError, match="asset_manifest"):
        write_checkpoint(pipeline_dir, project_id, "edit", "completed",
                         {"edit_decisions": decisions}, pipeline_type="character-film")
    for stage, stage_artifacts in (
        ("edit", {"edit_decisions": decisions, "asset_manifest": assets}),
        ("compose", {"render_report": report}),
        ("final_review", {"final_review": final_review}),
    ):
        write_checkpoint(pipeline_dir, project_id, stage, "completed", stage_artifacts,
                         pipeline_type="character-film")
    assert get_next_stage(pipeline_dir, project_id, "character-film") is None
    assert len(get_completed_stages(pipeline_dir, project_id, "character-film")) == 11
    output.write_bytes(b"render was replaced")
    assert get_next_stage(pipeline_dir, project_id, "character-film") == "compose"
