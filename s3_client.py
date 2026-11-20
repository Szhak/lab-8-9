"""S3 operations for the local MinIO instance used by this lab."""

import os
import time
from contextlib import closing
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


BUCKET_NAME = os.getenv("LAB_S3_BUCKET", "distributed-course-bucket")

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("LAB_S3_ENDPOINT", "http://localhost:9001"),
    aws_access_key_id=os.getenv("LAB_S3_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.getenv("LAB_S3_SECRET_KEY", "minioadminpassword"),
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        connect_timeout=2,
        read_timeout=10,
    ),
    region_name="us-east-1",
)


def init_storage() -> None:
    """Create the configured bucket if it does not already exist."""
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        return
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
    except ClientError as error:
        if error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise


def upload_object(
    key_name: str, file_path: str | Path, metadata: dict[str, str] | None = None
) -> float:
    """Upload a file and return elapsed seconds."""
    started = time.perf_counter()
    s3.upload_file(
        Filename=str(file_path),
        Bucket=BUCKET_NAME,
        Key=key_name,
        ExtraArgs={"Metadata": metadata or {}},
    )
    return time.perf_counter() - started


def read_object(key_name: str) -> bytes:
    """Fetch the complete object body with GET."""
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key_name)
    with closing(response["Body"]) as body:
        return body.read()


def read_object_metadata(key_name: str) -> dict[str, str]:
    """Fetch custom metadata with HEAD, without transferring the body."""
    response = s3.head_object(Bucket=BUCKET_NAME, Key=key_name)
    return response["Metadata"]


def wait_for_object(key_name: str, expected_content: bytes, timeout: float = 3.0) -> float:
    """Measure how long GET takes to return the expected version after a write."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    started = time.perf_counter()
    deadline = started + timeout
    while time.perf_counter() < deadline:
        try:
            content = read_object(key_name)
        except ClientError as error:
            if error.response["Error"]["Code"] not in {"404", "NoSuchKey", "NotFound"}:
                raise
        else:
            elapsed = time.perf_counter() - started
            if content == expected_content and elapsed <= timeout:
                return elapsed

        remaining = deadline - time.perf_counter()
        if remaining > 0:
            time.sleep(min(0.05, remaining))

    raise TimeoutError(f"Expected version of {key_name!r} was not read within {timeout:g} s")
