"""S3 storage backend for skill archives."""

import boto3
from botocore.exceptions import ClientError

from .config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=settings.REGION)
    return _client


def upload(key: str, data: bytes) -> None:
    _get_client().put_object(
        Bucket=settings.BUCKET_NAME,
        Key=key,
        Body=data,
    )


def download(key: str) -> bytes | None:
    try:
        resp = _get_client().get_object(
            Bucket=settings.BUCKET_NAME,
            Key=key,
        )
        return resp["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def exists(key: str) -> bool:
    try:
        _get_client().head_object(Bucket=settings.BUCKET_NAME, Key=key)
        return True
    except ClientError:
        return False


def delete(key: str) -> None:
    _get_client().delete_object(Bucket=settings.BUCKET_NAME, Key=key)
