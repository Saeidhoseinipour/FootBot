"""Tests for the player photo storage logic (no Telegram needed)."""

import json
import os

from photos import (
    expected_path,
    get_photo_path,
    load_index,
    player_slug,
    remove_photo,
    set_photo,
)


def test_player_slug():
    assert player_slug("Mohammd Hosein") == "Mohammd_Hosein"
    assert player_slug("Saeid") == "Saeid"


def test_set_and_get_photo(tmp_path):
    photos_dir = tmp_path / "photos"
    index_file = tmp_path / "index.json"
    path = set_photo("Sahand", "FILE_ID_1", str(photos_dir), str(index_file))

    # The bot downloads the photo to the returned path; simulate that here.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"fake-jpeg")

    assert os.path.exists(path)
    assert get_photo_path("Sahand", str(photos_dir)) == path

    index = load_index(str(index_file))
    assert index["Sahand"] == {"file_id": "FILE_ID_1", "path": path}


def test_get_photo_returns_none_for_missing(tmp_path):
    assert get_photo_path("Nobody", str(tmp_path)) is None


def test_remove_photo_deletes_file_and_index(tmp_path):
    photos_dir = tmp_path / "photos"
    index_file = tmp_path / "index.json"
    path = set_photo("Hani", "F2", str(photos_dir), str(index_file))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"fake-jpeg")
    assert os.path.exists(path)

    assert remove_photo("Hani", str(photos_dir), str(index_file)) is True
    assert not os.path.exists(path)
    assert load_index(str(index_file)) == {}
    assert get_photo_path("Hani", str(photos_dir)) is None


def test_remove_photo_missing_player(tmp_path):
    assert remove_photo("Nobody", str(tmp_path), str(tmp_path / "index.json")) is False


def test_expected_path_uses_slug(tmp_path):
    assert expected_path("Mohammad Reza", str(tmp_path)).endswith("Mohammad_Reza.jpg")