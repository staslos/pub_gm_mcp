from __future__ import annotations
import json
from pathlib import Path
from pub_gm_mcp.models.adventure import Adventure


class AdventureParser:
    """Loads and saves Adventure data from/to JSON files."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load(self, adventure_id: str) -> Adventure:
        path = self._path(adventure_id)
        if not path.exists():
            raise FileNotFoundError(f"Adventure '{adventure_id}' not found at {path}")
        return Adventure.model_validate_json(path.read_text())

    def save(self, adventure: Adventure) -> None:
        self._path(adventure.id).write_text(
            adventure.model_dump_json(indent=2)
        )

    def list_adventures(self) -> list[str]:
        return [p.stem for p in self.data_dir.glob("*.json")]

    def create(self, adventure: Adventure) -> None:
        path = self._path(adventure.id)
        if path.exists():
            raise FileExistsError(f"Adventure '{adventure.id}' already exists")
        self.save(adventure)

    def delete(self, adventure_id: str) -> None:
        path = self._path(adventure_id)
        if not path.exists():
            raise FileNotFoundError(f"Adventure '{adventure_id}' not found")
        path.unlink()

    def _path(self, adventure_id: str) -> Path:
        return self.data_dir / f"{adventure_id}.json"
