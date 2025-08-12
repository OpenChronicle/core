import json
from pathlib import Path

from openchronicle.infrastructure.images.processing.storage_manager import ImageStorageManager


def test_load_metadata_with_invalid_json_returns_empty(tmp_path: Path):
    story_dir = tmp_path / "story"
    images_dir = story_dir / "images"
    images_dir.mkdir(parents=True)

    # Write malformed JSON to images.json
    metadata_file = images_dir / "images.json"
    metadata_file.write_text("{ this is: not json", encoding="utf-8")

    mgr = ImageStorageManager(str(story_dir))
    assert mgr.metadata == {}


def test_delete_image_missing_returns_false(tmp_path: Path):
    story_dir = tmp_path / "story"
    # Manager will create required subdirectories
    mgr = ImageStorageManager(str(story_dir))

    assert mgr.delete_image("nonexistent") is False
