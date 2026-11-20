from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from s3_client import (
    BUCKET_NAME,
    init_storage,
    read_object,
    read_object_metadata,
    s3,
    upload_object,
    wait_for_object,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_bucket():
    init_storage()


@pytest.fixture
def object_key():
    key = f"pytest/{uuid4().hex}/sample.bin"
    yield key
    s3.delete_object(Bucket=BUCKET_NAME, Key=key)


def test_s3_bucket_existence():
    buckets = s3.list_buckets()["Buckets"]
    assert BUCKET_NAME in {bucket["Name"] for bucket in buckets}


def test_s3_object_upload_and_read(tmp_path, object_key):
    content = b"Stream Data Content\x00\xff"
    payload = tmp_path / "sample.bin"
    payload.write_bytes(content)

    assert upload_object(object_key, payload) >= 0
    assert read_object(object_key) == content


def test_s3_custom_metadata(tmp_path, object_key):
    payload = tmp_path / "sample.bin"
    payload.write_bytes(b"Metadata sample")
    metadata = {"course": "CSS4004", "storage": "minio"}

    upload_object(object_key, payload, metadata)

    assert read_object_metadata(object_key) == metadata


def test_s3_overwrite_visibility_within_bound(tmp_path, object_key):
    payload = tmp_path / "sample.bin"
    payload.write_bytes(b"first version")
    upload_object(object_key, payload)
    assert read_object(object_key) == b"first version"

    updated_content = b"second version"
    payload.write_bytes(updated_content)
    upload_object(object_key, payload)

    assert 0 <= wait_for_object(object_key, updated_content, timeout=3.0) <= 3.0


def test_s3_object_can_be_deleted(object_key):
    s3.put_object(Bucket=BUCKET_NAME, Key=object_key, Body=b"delete me")
    assert read_object(object_key) == b"delete me"

    s3.delete_object(Bucket=BUCKET_NAME, Key=object_key)

    with pytest.raises(ClientError) as failure:
        read_object(object_key)
    assert failure.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404
