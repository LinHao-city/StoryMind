"""Seedance provider error handling."""

from __future__ import annotations

import requests

from tools.video.seedance_video import SeedanceVideo


def test_content_policy_error_is_explicit_without_echoing_media(monkeypatch, tmp_path):
    monkeypatch.setenv("FAL_KEY", "test-key")

    response = requests.Response()
    response.status_code = 422
    response.url = "https://queue.fal.run/bytedance/seedance-2.0/requests/test"
    response._content = (
        b'{"detail":[{"type":"content_policy_violation",'
        b'"msg":"The images may contain likenesses of real people.",'
        b'"input":{"image_urls":["https://private.example/child.png"]}}]}'
    )
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    result = SeedanceVideo().execute({
        "prompt": "A garden scene", "operation": "reference_to_video",
        "reference_image_urls": ["https://private.example/child.png"],
        "output_path": str(tmp_path / "clip.mp4"),
    })

    assert not result.success
    assert "content policy" in result.error.lower()
    assert "likenesses of real people" in result.error
    assert "private.example" not in result.error
