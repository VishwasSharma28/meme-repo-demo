import boto3
import json
import zipfile
import time

ENDPOINT = "http://localhost:4566"

iam = boto3.client(
    "iam",
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1"
)

lam = boto3.client(
    "lambda",
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1"
)

# Create Lambda execution role
role_name = "demo-lambda-role"

try:
    role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        })
    )
    role_arn = role["Role"]["Arn"]
except iam.exceptions.EntityAlreadyExistsException:
    role_arn = iam.get_role(RoleName=role_name)["Role"]["Arn"]

# Package the Lambda code
with zipfile.ZipFile("lambda.zip", "w") as z:
    z.write("lambda_function.py")

with open("lambda.zip", "rb") as f:
    code = f.read()

# Deploy Lambda
try:
    lam.create_function(
        FunctionName="hello-demo",
        Runtime="python3.12",
        Role=role_arn,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": code},
        Timeout=10
    )
    print("Lambda deployed!")
except lam.exceptions.ResourceConflictException:
    lam.update_function_code(
        FunctionName="hello-demo",
        ZipFile=code
    )
    print("Lambda updated!")

# Wait until Lambda becomes active
for _ in range(30):
    state = lam.get_function(
        FunctionName="hello-demo"
    )["Configuration"]["State"]

    print("Lambda state:", state)

    if state == "Active":
        break

    time.sleep(2)
else:
    raise RuntimeError("Lambda did not become active in time")

# Invoke Lambda
response = lam.invoke(
    FunctionName="hello-demo",
    Payload=json.dumps({"name": "Vishwas"})
)

print("\nLambda response:")
print(response["Payload"].read().decode())