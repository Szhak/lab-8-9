"""Measure end-to-end reads of the same payload through WebHDFS and S3."""

import hashlib
import json
import time
from collections.abc import Callable
from contextlib import closing
from typing import BinaryIO
from urllib.request import urlopen

from s3_client import BUCKET_NAME, s3


KEY = "sample_100m.bin"
HDFS_URL = f"http://namenode:9870/webhdfs/v1/user/student/data/{KEY}?op=OPEN&user.name=root"
CHUNK_SIZE = 1024 * 1024
RUNS = 5


def open_hdfs() -> BinaryIO:
    return urlopen(HDFS_URL, timeout=20)


def open_minio() -> BinaryIO:
    return s3.get_object(Bucket=BUCKET_NAME, Key=KEY)["Body"]


def measure(open_body: Callable[[], BinaryIO]) -> tuple[float, int, str]:
    checksum = hashlib.sha256()
    total_bytes = 0
    start = time.perf_counter()
    with closing(open_body()) as body:
        while chunk := body.read(CHUNK_SIZE):
            total_bytes += len(chunk)
            checksum.update(chunk)
    return (time.perf_counter() - start) * 1000, total_bytes, checksum.hexdigest()


def main() -> None:
    _, expected_size, expected_digest = measure(open_hdfs)
    _, minio_size, minio_digest = measure(open_minio)
    if (minio_size, minio_digest) != (expected_size, expected_digest):
        raise ValueError("HDFS and MinIO contain different payloads")

    samples = {"hdfs_ms": [], "s3_ms": []}
    methods = (("hdfs_ms", open_hdfs), ("s3_ms", open_minio))
    for index in range(RUNS):
        order = methods if index % 2 == 0 else reversed(methods)
        for storage, open_body in order:
            elapsed, size, digest = measure(open_body)
            if (size, digest) != (expected_size, expected_digest):
                raise ValueError(f"Payload changed during {storage} measurement")
            samples[storage].append(round(elapsed, 2))

    print(json.dumps({**samples, "payload_bytes": expected_size}, indent=2))


if __name__ == "__main__":
    main()
