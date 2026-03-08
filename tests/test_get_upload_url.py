import json
import importlib
import boto3
from moto import mock_aws
from tests.constants import BUCKET_NAME


class TestGetUploadUrl:

    @mock_aws
    def test_returns_presigned_url(self):
        """Happy path: filename + valid content type returns a presigned URL."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {
            'queryStringParameters': {
                'filename': 'photo.jpg',
                'contentType': 'image/jpeg',
            }
        }
        result = mod.lambda_handler(event, None)
        body = json.loads(result['body'])

        assert result['statusCode'] == 200
        assert 'uploadUrl' in body
        assert 'key' in body
        assert body['key'].startswith('uploads/')
        assert 'photo.jpg' in body['key']

    @mock_aws
    def test_missing_filename_returns_400(self):
        """Missing filename should return 400."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {'queryStringParameters': {}}
        result = mod.lambda_handler(event, None)
        body = json.loads(result['body'])

        assert result['statusCode'] == 400
        assert 'error' in body

    @mock_aws
    def test_no_query_params_returns_400(self):
        """No query params at all should return 400."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {'queryStringParameters': None}
        result = mod.lambda_handler(event, None)

        assert result['statusCode'] == 400

    @mock_aws
    def test_invalid_content_type_returns_400(self):
        """Unsupported content type should return 400."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {
            'queryStringParameters': {
                'filename': 'hack.exe',
                'contentType': 'application/octet-stream',
            }
        }
        result = mod.lambda_handler(event, None)
        body = json.loads(result['body'])

        assert result['statusCode'] == 400
        assert 'Invalid content type' in body['error']

    @mock_aws
    def test_default_content_type_is_jpeg(self):
        """If contentType omitted, defaults to image/jpeg."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {
            'queryStringParameters': {
                'filename': 'photo.jpg',
            }
        }
        result = mod.lambda_handler(event, None)

        assert result['statusCode'] == 200

    @mock_aws
    def test_cors_headers_present(self):
        """Response should include CORS headers."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {
            'queryStringParameters': {
                'filename': 'test.png',
                'contentType': 'image/png',
            }
        }
        result = mod.lambda_handler(event, None)

        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        assert result['headers']['Content-Type'] == 'application/json'

    @mock_aws
    def test_unique_keys_per_upload(self):
        """Each call should generate a unique S3 key (UUID prefix)."""
        boto3.client('s3', region_name='us-east-1').create_bucket(Bucket=BUCKET_NAME)

        import lambdas.get_upload_url as mod
        importlib.reload(mod)

        event = {
            'queryStringParameters': {
                'filename': 'same.jpg',
                'contentType': 'image/jpeg',
            }
        }
        r1 = json.loads(mod.lambda_handler(event, None)['body'])
        r2 = json.loads(mod.lambda_handler(event, None)['body'])

        assert r1['key'] != r2['key']
