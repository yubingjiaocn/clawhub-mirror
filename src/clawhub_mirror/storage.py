"""Storage backends for skill archives.

Provides an abstract interface and two concrete implementations:
- LocalStorage: stores files on the local filesystem
- S3Storage: stores files in S3-compatible object storage (including MinIO)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from clawhub_mirror.config import Settings


class StorageBackend(ABC):
    """Abstract base for skill archive storage."""

    @abstractmethod
    async def upload(self, key: str, data: bytes) -> None:
        """Upload data to the given storage key.

        Args:
            key: The storage path/key for the file.
            data: Raw bytes to store.
        """

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data from the given storage key.

        Args:
            key: The storage path/key to retrieve.

        Returns:
            The raw bytes of the stored file.

        Raises:
            FileNotFoundError: If the key does not exist.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object at the given storage key.

        Args:
            key: The storage path/key to delete.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether an object exists at the given key.

        Args:
            key: The storage path/key to check.

        Returns:
            True if the object exists, False otherwise.
        """


class LocalStorage(StorageBackend):
    """Store skill archives on the local filesystem."""

    def __init__(self, base_path: str) -> None:
        """Initialize local storage.

        Args:
            base_path: Root directory for stored files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a storage key to an absolute file path."""
        return self.base_path / key

    async def upload(self, key: str, data: bytes) -> None:
        """Write data to a local file."""
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(target.write_bytes, data))

    async def download(self, key: str) -> bytes:
        """Read data from a local file."""
        target = self._resolve(key)
        if not target.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, target.read_bytes)

    async def delete(self, key: str) -> None:
        """Delete a local file."""
        target = self._resolve(key)
        if target.exists():
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, target.unlink)

    async def exists(self, key: str) -> bool:
        """Check if a local file exists."""
        target = self._resolve(key)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, target.exists)


class S3Storage(StorageBackend):
    """Store skill archives in an S3-compatible object store."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "us-east-1",
    ) -> None:
        """Initialize S3 storage.

        Args:
            bucket: S3 bucket name.
            endpoint_url: Custom endpoint URL (e.g. for MinIO). Empty uses AWS default.
            access_key: AWS access key ID.
            secret_key: AWS secret access key.
            region: AWS region name.
        """
        self.bucket = bucket

        client_kwargs: dict[str, str] = {"region_name": region}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self._client = boto3.client("s3", **client_kwargs)

    async def upload(self, key: str, data: bytes) -> None:
        """Upload data to S3."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            partial(self._client.put_object, Bucket=self.bucket, Key=key, Body=data),
        )

    async def download(self, key: str) -> bytes:
        """Download data from S3."""
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(self._client.get_object, Bucket=self.bucket, Key=key),
        )
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        """Delete an object from S3."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            partial(self._client.delete_object, Bucket=self.bucket, Key=key),
        )

    async def exists(self, key: str) -> bool:
        """Check if an object exists in S3."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(self._client.head_object, Bucket=self.bucket, Key=key),
            )
            return True
        except self._client.exceptions.ClientError:
            return False


def create_storage(settings: Settings) -> StorageBackend:
    """Create a storage backend based on application settings.

    Args:
        settings: Application settings specifying the backend type and credentials.

    Returns:
        A configured StorageBackend instance.

    Raises:
        ValueError: If the configured storage_backend is not recognized.
    """
    if settings.storage_backend == "local":
        return LocalStorage(base_path=settings.storage_local_path)

    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )

    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
