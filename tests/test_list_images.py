import json
import importlib
import boto3
from moto import mock_aws
from tests.constants import BUCKET_NAME, TABLE_NAME


class TestListImages:

    @mock_aws
    def test_returns_empty_list(self):
        """No images in DynamoDB returns empty list."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)
        dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        import lambdas.list_images as mod
        importlib.reload(mod)

        result = mod.lambda_handler({}, None)
        body = json.loads(result['body'])

        assert result['statusCode'] == 200
        assert body['count'] == 0
        assert body['images'] == []

    @mock_aws
    def test_returns_images_sorted_newest_first(self):
        """Images should come back sorted by timestamp descending."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)
        dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table = dynamo.Table(TABLE_NAME)

        table.put_item(Item={
            'imageId': '1',
            'filename': 'old.jpg',
            's3Key': 'processed/old.jpg',
            'timestamp': '2026-01-01T00:00:00',
        })
        table.put_item(Item={
            'imageId': '2',
            'filename': 'new.jpg',
            's3Key': 'processed/new.jpg',
            'timestamp': '2026-03-01T00:00:00',
        })

        import lambdas.list_images as mod
        importlib.reload(mod)

        result = mod.lambda_handler({}, None)
        body = json.loads(result['body'])

        assert body['count'] == 2
        assert body['images'][0]['filename'] == 'new.jpg'
        assert body['images'][1]['filename'] == 'old.jpg'

    @mock_aws
    def test_images_have_presigned_urls(self):
        """Each image should have a presigned URL."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)
        dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table = dynamo.Table(TABLE_NAME)

        table.put_item(Item={
            'imageId': 'abc',
            'filename': 'photo.png',
            's3Key': 'processed/photo.png',
            'timestamp': '2026-02-01T00:00:00',
        })

        import lambdas.list_images as mod
        importlib.reload(mod)

        result = mod.lambda_handler({}, None)
        body = json.loads(result['body'])

        img = body['images'][0]
        assert 'url' in img
        assert BUCKET_NAME in img['url']
        assert img['imageId'] == 'abc'
        assert img['filename'] == 'photo.png'
        assert img['timestamp'] == '2026-02-01T00:00:00'

    @mock_aws
    def test_skips_items_without_s3key(self):
        """Items missing s3Key should be skipped."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)
        dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        table = dynamo.Table(TABLE_NAME)

        table.put_item(Item={'imageId': 'no-key', 'filename': 'broken.jpg'})
        table.put_item(Item={
            'imageId': 'has-key',
            'filename': 'good.jpg',
            's3Key': 'processed/good.jpg',
            'timestamp': '2026-01-01T00:00:00',
        })

        import lambdas.list_images as mod
        importlib.reload(mod)

        result = mod.lambda_handler({}, None)
        body = json.loads(result['body'])

        assert body['count'] == 1
        assert body['images'][0]['filename'] == 'good.jpg'

    @mock_aws
    def test_cors_headers(self):
        """Response should include CORS headers."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)
        dynamo = boto3.resource('dynamodb', region_name='us-east-1')
        dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'imageId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'imageId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        import lambdas.list_images as mod
        importlib.reload(mod)

        result = mod.lambda_handler({}, None)

        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        assert result['headers']['Content-Type'] == 'application/json'
