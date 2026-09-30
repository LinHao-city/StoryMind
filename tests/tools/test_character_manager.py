"""Local character record and photo privacy behavior."""

from __future__ import annotations

from tools.planning.character_manager import CharacterManager


def test_private_photo_defaults_and_remote_permission(tmp_path):
    manager = CharacterManager()
    result = manager.execute({
        "action": "draft", "project_dir": str(tmp_path), "id": "grandchild",
        "role": "lead", "age_category": "minor", "source_type": "private_family_photo",
    })
    assert result.success
    character = result.data["character"]
    assert character["source"]["source_photos_local_only"] is True
    assert character["source"]["remote_character_creation_allowed"] is False
    assert character["source"]["downstream_use_original_photos"] is False

    character["source"]["source_photos_local_only"] = False
    character["source"]["remote_character_creation_allowed"] = True
    rejected = manager.execute({"action": "save", "project_dir": str(tmp_path), "character": character})
    assert not rejected.success
    assert "approval" in rejected.error
    character["source"]["remote_character_creation_approval"] = {
        "approved_by": "user", "approved_at": "2026-09-29T00:00:00Z", "provider": "specific-provider",
    }
    saved = manager.execute({"action": "save", "project_dir": str(tmp_path), "character": character})
    assert saved.success
    loaded = manager.execute({"action": "load", "project_dir": str(tmp_path), "character_id": "grandchild"})
    assert loaded.success and loaded.data["character"] == character

    character["source"]["downstream_use_original_photos"] = True
    rejected = manager.execute({"action": "save", "project_dir": str(tmp_path), "character": character})
    assert not rejected.success and "approval" in rejected.error
    character["source"]["downstream_original_approval"] = {
        "approved_by": "user", "approved_at": "2026-09-29T00:00:00Z", "provider": "specific-provider",
    }
    assert manager.execute({"action": "save", "project_dir": str(tmp_path), "character": character}).success


def test_character_paths_and_missing_references_fail(tmp_path):
    manager = CharacterManager()
    character = manager.draft("actor", "lead")
    character["status"] = "AWAITING_APPROVAL"
    character["required_outfits"] = ["daywear"]
    rejected = manager.execute({"action": "lock", "project_dir": str(tmp_path),
                                "character": character, "approved_by": "user"})
    assert not rejected.success
    assert "master identity" in rejected.error
    character["id"] = "../escape"
    rejected = manager.execute({"action": "save", "project_dir": str(tmp_path), "character": character})
    assert not rejected.success
