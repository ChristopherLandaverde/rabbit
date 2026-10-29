"""Dataset storage backends."""

from .local import LocalDiskStorage
from .s3 import S3Storage

__all__ = ["LocalDiskStorage", "S3Storage"]
