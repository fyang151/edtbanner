import os
import pytest
import boto3
from moto import mock_aws
from tests.constants import TINY_PNG, BUCKET_NAME, TABLE_NAME, REGION


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Set env vars and fake AWS credentials for all tests."""
    monkeypatch.setenv('S3_BUCKET', BUCKET_NAME)
    monkeypatch.setenv('DYNAMODB_TABLE', TABLE_NAME)
    monkeypatch.setenv('AWS_DEFAULT_REGION', REGION)
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')


@pytest.fixture
def s3(aws_env):
    """Create a mocked S3 bucket."""
    with mock_aws():
        client = boto3.client('s3', region_name=REGION)
        client.create_bucket(Bucket=BUCKET_NAME)
        yield client


@pytest.fixture
def dynamodb_table(aws_env):
    """Create a mocked DynamoDB table."""
    with mock_aws():
        resource = boto3.resource('dynamodb', region_name=REGION)
        table = resource.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        yield table


@pytest.fixture
def s3_and_dynamodb(aws_env):
    """Create both S3 and DynamoDB mocks in the same context."""
    with mock_aws():
        s3_client = boto3.client('s3', region_name=REGION)
        s3_client.create_bucket(Bucket=BUCKET_NAME)

        resource = boto3.resource('dynamodb', region_name=REGION)
        table = resource.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)

        yield s3_client, table
