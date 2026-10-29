"""Storage interface and key construction for uploaded datasets."""

from typing import Protocol


def dataset_storage_key(key_id: str, dataset_id: str, extension: str) -> str:
    extension = extension.lower().lstrip(".")
    return f"{key_id}/{dataset_id}.{extension}"


class DatasetStorage(Protocol):
    def put(self, key: str, content: bytes) -> str: ...

    def read(self, uri: str) -> bytes: ...
