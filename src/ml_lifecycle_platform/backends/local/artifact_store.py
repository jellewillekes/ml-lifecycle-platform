"""File-backed `ArtifactStore` implementation used by the local runtime
profile; rooted under the configured artifacts directory."""

from __future__ import annotations

from pathlib import Path


class LocalArtifactStore:
    """File-backed artifact store rooted under the local artifact directory."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, path: str) -> Path:
        return self._root / path

    def write_bytes(self, path: str, content: bytes) -> None:
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def read_bytes(self, path: str) -> bytes:
        return self.resolve(path).read_bytes()
