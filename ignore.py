import uuid
from pathlib import Path
from typing import List

IGNORE_FILE_NAME = ".fileignore"
IGNORE_FILE_PATH = Path(__file__).parent / IGNORE_FILE_NAME


def _ensure_file() -> None:
    if not IGNORE_FILE_PATH.exists():
        IGNORE_FILE_PATH.touch()


def _normalize_id(id_str: str) -> str:
    # Validate and normalize to canonical UUID string (lowercase, hyphenated)
    try:
        return str(uuid.UUID(id_str))
    except ValueError as e:
        raise ValueError(f"Invalid UUID: {id_str}") from e


def add_ignore_id(id_str: str) -> None:
    """
    Add a UUID to the ignore list stored in .fileignore.
    Deduplicates entries and validates UUID format.
    """
    _ensure_file()
    normalized = _normalize_id(id_str)

    # Read existing IDs
    existing = set()
    with IGNORE_FILE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                existing.add(str(uuid.UUID(s)))
            except ValueError:
                # Skip malformed lines silently
                continue

    if normalized in existing:
        return

    # Append the new ID
    with IGNORE_FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(normalized + "\n")


def get_ignored_ids() -> List[str]:
    """
    Return a list of UUID strings currently in the ignore list.
    Skips malformed lines.
    """
    _ensure_file()
    ids: List[str] = []
    with IGNORE_FILE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                ids.append(str(uuid.UUID(s)))
            except ValueError:
                continue
    return ids


def is_ignored(id_str: str) -> bool:
    """
    Return True if the given UUID is present in the .fileignore list.
    """
    _ensure_file()
    normalized = _normalize_id(id_str)
    return normalized in set(get_ignored_ids())
