"""S3-compatible storage backend."""

import boto3


class S3Storage:
    def __init__(
        self, bucket: str, region: str | None = None, endpoint_url: str | None = None
    ):
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def put(self, key: str, content: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return f"s3://{self.bucket}/{key}"

    def read(self, uri: str) -> bytes:
        bucket, _, key = uri[5:].partition("/")
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
