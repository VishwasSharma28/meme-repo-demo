
import json
import zipfile
import boto3
from botocore.exceptions import ClientError

ENDPOINT = "http://localhost:4566"
REGION = "us-east-1"

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

dynamodb = boto3.client(
    "dynamodb",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

lambda_client = boto3.client(
    "lambda",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

iam = boto3.client(
    "iam",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

BUCKET = "meme-uploads"
TABLE = "MemeMetadata"
FUNCTION = "process-meme-upload"
ROLE = "meme-lambda-role"


# 1. Create the S3 bucket.
try:
    s3.create_bucket(Bucket=BUCKET)
    print("Created S3 bucket")
except ClientError as error:
    if error.response["Error"]["Code"] not in (
        "BucketAlreadyOwnedByYou",
        "BucketAlreadyExists",
    ):
        raise
    print("S3 bucket already exists")


# 2. Create the DynamoDB table.
try:
    dynamodb.create_table(
        TableName=TABLE,
        KeySchema=[
            {"AttributeName": "object_key", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "object_key", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print("Created DynamoDB table")
except ClientError as error:
    if error.response["Error"]["Code"] != "ResourceInUseException":
        raise
    print("DynamoDB table already exists")


# 3. Create the Lambda execution role.
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
}

try:
    role = iam.create_role(
        RoleName=ROLE,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
    )
    print("Created Lambda role")
except ClientError as error:
    if error.response["Error"]["Code"] != "EntityAlreadyExists":
        raise
    role = iam.get_role(RoleName=ROLE)
    print("Lambda role already exists")

role_arn = role["Role"]["Arn"]


# 4. Package the Lambda function.
with zipfile.ZipFile("lambda.zip", "w") as archive:
    archive.write("lambda_function.py")

with open("lambda.zip", "rb") as file:
    code = file.read()


# 5. Create or update the Lambda function.
try:
    lambda_client.create_function(
        FunctionName=FUNCTION,
        Runtime="python3.11",
        Role=role_arn,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": code},
        Timeout=30,
        Environment={
            "Variables": {
                "LOCALSTACK_ENDPOINT": "http://host.docker.internal:4566"
            }
        },
    )
    print("Created Lambda function")
except ClientError as error:
    if error.response["Error"]["Code"] != "ResourceConflictException":
        raise

    lambda_client.update_function_code(
        FunctionName=FUNCTION,
        ZipFile=code,
    )
    print("Updated Lambda code")


# 6. Allow S3 to invoke Lambda.
try:
    lambda_client.add_permission(
        FunctionName=FUNCTION,
        StatementId="allow-s3-invoke",
        Action="lambda:InvokeFunction",
        Principal="s3.amazonaws.com",
        SourceArn=f"arn:aws:s3:::{BUCKET}",
    )
except ClientError as error:
    if error.response["Error"]["Code"] != "ResourceConflictException":
        raise


# 7. Configure S3 upload events.
lambda_arn = lambda_client.get_function(
    FunctionName=FUNCTION
)["Configuration"]["FunctionArn"]

s3.put_bucket_notification_configuration(
    Bucket=BUCKET,
    NotificationConfiguration={
        "LambdaFunctionConfigurations": [{
            "LambdaFunctionArn": lambda_arn,
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "uploads/"}
                    ]
                }
            },
        }]
    },
)

print("\nDeployment complete!")
print("Upload memes to s3://meme-uploads/uploads/")
