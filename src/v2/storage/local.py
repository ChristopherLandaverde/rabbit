"""Local disk storage for development and tests."""

from pathlib import Path


class LocalDiskStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def put(self, key: str, content: bytes) -> str:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target)

    def read(self, uri: str) -> bytes:
        return Path(uri).read_bytes()
