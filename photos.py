"""Player photo storage: photos are downloaded into player_photos/ with a JSON index."""

import json
import logging
import os

logger = logging.getLogger(__name__)

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_photos")
INDEX_FILE = os.path.join(PHOTOS_DIR, "index.json")


def player_slug(player: str) -> str:
    """Build a safe filename from a player name (keeps it readable)."""
    return player.replace(" ", "_").replace("/", "_")


def load_index(index_file: str | None = None) -> dict:
    """Read the photo index, or an empty dict if absent/corrupt."""
    index_file = index_file or INDEX_FILE
    if os.path.exists(index_file):
        try:
            with open(index_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read photo index %s", index_file)
    return {}


def save_index(index: dict, index_file: str | None = None) -> None:
    """Write the photo index to disk."""
    index_file = index_file or INDEX_FILE
    os.makedirs(os.path.dirname(index_file), exist_ok=True)
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def expected_path(player: str, photos_dir: str | None = None) -> str:
    photos_dir = photos_dir or PHOTOS_DIR
    return os.path.join(photos_dir, f"{player_slug(player)}.jpg")


def set_photo(
    player: str,
    file_id: str,
    photos_dir: str | None = None,
    index_file: str | None = None,
) -> str:
    """Record a player's photo (file_id) in the index. Returns the file path."""
    path = expected_path(player, photos_dir)
    index = load_index(index_file)
    index[player] = {"file_id": file_id, "path": path}
    save_index(index, index_file)
    return path


def get_photo_path(player: str, photos_dir: str | None = None) -> str | None:
    """Path of a player's downloaded photo, or None if not uploaded."""
    path = expected_path(player, photos_dir)
    return path if os.path.exists(path) else None


def remove_photo(
    player: str,
    photos_dir: str | None = None,
    index_file: str | None = None,
) -> bool:
    """Delete a player's photo file and index entry. Returns True if removed."""
    removed = False
    index = load_index(index_file)
    if player in index:
        del index[player]
        save_index(index, index_file)
        removed = True
    path = expected_path(player, photos_dir)
    if os.path.exists(path):
        os.remove(path)
        removed = True
    return removed