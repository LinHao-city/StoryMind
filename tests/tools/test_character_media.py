"""Photo intake remains local and generated assets retain provenance."""

from pathlib import Path

from PIL import Image

from tools.planning.character_manager import CharacterManager
from tools.planning.character_media import CharacterMedia


def test_source_intake_and_agent_native_registration(tmp_path):
    photo = tmp_path / "photo.png"
    Image.new("RGB", (16, 16), "blue").save(photo)
    character = CharacterManager.draft("hero", "lead", "minor", "private_family_photo")
    project = tmp_path / "project"
    tool = CharacterMedia()

    intake = tool.execute({"action": "intake_source", "project_dir": str(project),
                           "character": character, "input_path": str(photo)})
    assert intake.success
    source = intake.data["asset"]
    assert source["origin"] == "user_source"
    assert (project / source["path"]).is_file()
    assert source["path"].startswith("characters/hero/source/")

    generated_photo = tmp_path / "generated.png"
    Image.new("RGB", (16, 16), "green").save(generated_photo)
    generated = tool.execute({
        "action": "register_generated", "project_dir": str(project),
        "character": character, "input_path": str(generated_photo), "category": "candidate",
        "asset_id": "candidate-1", "provider": "codex-agent-native",
        "model": "host-imagegen", "prompt": "Fictional character in blue coat", "seed": 42,
    })
    assert generated.success
    record = generated.data["asset"]
    assert record["origin"] == "generated"
    assert record["provider"] == "codex-agent-native"
    assert record["sha256"] != source["sha256"]
    assert (project / record["path"]).is_file()

    relabeled = tool.execute({
        "action": "register_generated", "project_dir": str(project),
        "character": character, "input_path": str(photo), "category": "candidate",
        "asset_id": "candidate-2", "provider": "fake", "model": "fake", "prompt": "fake",
    })
    assert not relabeled.success
    assert "Source photo" in relabeled.error

    other_character = CharacterManager.draft("other", "supporting", "minor", "private_family_photo")
    cross_character = tool.execute({
        "action": "register_generated", "project_dir": str(project),
        "character": other_character, "input_path": str(photo), "category": "candidate",
        "asset_id": "candidate-1", "provider": "fake", "model": "fake", "prompt": "fake",
    })
    assert not cross_character.success
    assert "Source photo" in cross_character.error

    blocked = tool.execute({"action": "check_remote_source", "character": character,
                            "provider": "codex-agent-native"})
    assert not blocked.success
    character["source"].update({
        "source_photos_local_only": False,
        "remote_character_creation_allowed": True,
        "remote_character_creation_approval": {
            "approved_by": "user", "approved_at": "2026-09-29T00:00:00Z",
            "provider": "codex-agent-native",
        },
    })
    assert tool.execute({"action": "check_remote_source", "character": character,
                         "provider": "codex-agent-native"}).success
    assert not tool.execute({"action": "check_remote_source", "character": character,
                             "provider": "different-provider"}).success


def test_invalid_and_escaping_media_is_rejected(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    tool = CharacterMedia()
    character = CharacterManager.draft("hero", "lead")
    result = tool.execute({"action": "intake_source", "project_dir": str(tmp_path / "project"),
                           "character": character, "input_path": str(bad)})
    assert not result.success
    character["id"] = "../outside"
    image = tmp_path / "image.png"
    Image.new("RGB", (4, 4), "red").save(image)
    result = tool.execute({"action": "intake_source", "project_dir": str(tmp_path / "project"),
                           "character": character, "input_path": str(image)})
    assert not result.success
