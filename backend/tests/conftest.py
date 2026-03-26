"""Shared fixtures: moto-mocked DynamoDB + S3, FastAPI TestClient, auth helpers."""

import os

# Set env vars BEFORE any app imports
os.environ["TABLE_NAME"] = "clawhub-test"
os.environ["BUCKET_NAME"] = "clawhub-test-skills"
os.environ["REGION"] = "us-east-1"
os.environ["ENVIRONMENT"] = "test"

import io
import zipfile

import boto3
import pytest
from moto import mock_aws
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def aws_mocks():
    """Start moto mocks for DynamoDB + S3 and reset singletons between tests."""
    with mock_aws():
        # --- DynamoDB table ---
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="clawhub-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
                {"AttributeName": "GSI3PK", "AttributeType": "S"},
                {"AttributeName": "GSI3SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI3",
                    "KeySchema": [
                        {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # --- S3 bucket ---
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="clawhub-test-skills")

        # Reset module-level singletons so they pick up the moto mock
        from app import dynamodb as ddb_mod
        from app import storage as storage_mod

        ddb_mod._table = None
        storage_mod._client = None

        yield

        # Clean up singletons after the test
        ddb_mod._table = None
        storage_mod._client = None


@pytest.fixture()
def client(aws_mocks) -> TestClient:
    from app.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    """Seed an admin user directly in DynamoDB and return its API token."""
    from app.auth import generate_api_token, hash_password
    from app import dynamodb

    token = generate_api_token()
    dynamodb.put_user(
        username="testadmin",
        hashed_password=hash_password("adminpass"),
        role="admin",
        api_token=token,
    )
    return token


@pytest.fixture()
def publisher_token(client: TestClient) -> str:
    """Seed a publisher user directly in DynamoDB and return its API token."""
    from app.auth import generate_api_token, hash_password
    from app import dynamodb

    token = generate_api_token()
    dynamodb.put_user(
        username="testpublisher",
        hashed_password=hash_password("pubpass"),
        role="publisher",
        api_token=token,
    )
    return token


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_zip(content: bytes = b"hello world") -> io.BytesIO:
    """Create a minimal valid zip file in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("skill.md", content.decode("utf-8", errors="replace"))
    buf.seek(0)
    return buf
