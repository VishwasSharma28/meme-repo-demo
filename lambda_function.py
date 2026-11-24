import os
from urllib.parse import unquote_plus

import boto3


# The Lambda runs in a separate Docker container.
# host.docker.internal lets it reach LocalStack on the host.
ENDPOINT = os.environ.get(
    "LOCALSTACK_ENDPOINT",
    "http://host.docker.internal:4566"
)

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

table = dynamodb.Table("MemeMetadata")


def lambda_handler(event, context):
    # S3 sends an event containing the uploaded object's details.
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        # Ask S3 for the object's metadata.
        metadata = s3.head_object(Bucket=bucket, Key=key)

        # Save the metadata in DynamoDB.
        table.put_item(
            Item={
                "object_key": f"{bucket}/{key}",
                "bucket": bucket,
                "filename": key.split("/")[-1],
                "size": metadata["ContentLength"],
                "content_type": metadata.get(
                    "ContentType", "unknown"
                ),
                "uploaded_at": record["eventTime"],
            }
        )

        print(f"Saved metadata for {key}")

    return {"statusCode": 200, "body": "Meme metadata saved"}