import importlib
import boto3
from moto import mock_aws
from unittest.mock import MagicMock
from tests.constants import BUCKET_NAME, TABLE_NAME, TINY_PNG


def make_s3_event(bucket, key):
    """Build a fake S3 event like the one Lambda receives."""
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key},
                }
            }
        ]
    }


class TestProcessImageAccept:
    """Tests where Rekognition says the image is clean."""

    @mock_aws
    def test_clean_image_is_moved_to_processed(self):
        # Set up mocked S3
        real_s3 = boto3.client("s3", region_name="us-east-1")
        real_s3.create_bucket(Bucket=BUCKET_NAME)
        real_s3.put_object(Bucket=BUCKET_NAME, Key="uploads/test.jpg", Body=TINY_PNG)

        # Set up mocked DynamoDB
        real_dynamo = boto3.resource("dynamodb", region_name="us-east-1")
        real_dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "imageId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "imageId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Mock Rekognition (no moto support, use MagicMock)
        mock_rek = MagicMock()
        mock_rek.detect_moderation_labels.return_value = {"ModerationLabels": []}

        import lambdas.process_image as mod

        mod.s3_client = real_s3
        mod.rekognition_client = mock_rek
        mod.dynamodb = real_dynamo

        event = make_s3_event(BUCKET_NAME, "uploads/test.jpg")
        result = mod.lambda_handler(event, None)

        assert result["statusCode"] == 200

        # Image should be in processed/
        objs = real_s3.list_objects_v2(Bucket=BUCKET_NAME)
        keys = [o["Key"] for o in objs.get("Contents", [])]
        assert "processed/test.jpg" in keys
        assert "uploads/test.jpg" not in keys

        # DynamoDB should have a record
        table = real_dynamo.Table(TABLE_NAME)
        scan = table.scan()
        assert scan["Count"] == 1
        item = scan["Items"][0]
        assert item["s3Key"] == "processed/test.jpg"
        assert item["filename"] == "test.jpg"

    @mock_aws
    def test_skips_already_processed(self):
        """Files in processed/ should be skipped."""
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET_NAME)

        import lambdas.process_image as mod

        importlib.reload(mod)

        event = make_s3_event(BUCKET_NAME, "processed/already-done.jpg")
        result = mod.lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert "Already processed" in result["body"]


class TestProcessImageReject:
    """Tests where Rekognition flags the image."""

    @mock_aws
    def test_flagged_image_is_deleted(self):
        real_s3 = boto3.client("s3", region_name="us-east-1")
        real_s3.create_bucket(Bucket=BUCKET_NAME)
        real_s3.put_object(Bucket=BUCKET_NAME, Key="uploads/bad.jpg", Body=TINY_PNG)

        real_dynamo = boto3.resource("dynamodb", region_name="us-east-1")
        real_dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "imageId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "imageId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        mock_rek = MagicMock()
        mock_rek.detect_moderation_labels.return_value = {
            "ModerationLabels": [
                {"Name": "Violence", "Confidence": 95.0, "ParentName": ""},
            ]
        }

        import lambdas.process_image as mod

        mod.s3_client = real_s3
        mod.rekognition_client = mock_rek
        mod.dynamodb = real_dynamo

        event = make_s3_event(BUCKET_NAME, "uploads/bad.jpg")
        result = mod.lambda_handler(event, None)

        assert result["statusCode"] == 403
        assert "Violence" in result["body"]

        # Image should be deleted entirely
        objs = real_s3.list_objects_v2(Bucket=BUCKET_NAME)
        keys = [o["Key"] for o in objs.get("Contents", [])]
        assert "uploads/bad.jpg" not in keys
        assert "processed/bad.jpg" not in keys

        # DynamoDB should be empty
        table = real_dynamo.Table(TABLE_NAME)
        assert table.scan()["Count"] == 0

    @mock_aws
    def test_multiple_moderation_labels(self):
        """Multiple flags should all appear in the rejection message."""
        real_s3 = boto3.client("s3", region_name="us-east-1")
        real_s3.create_bucket(Bucket=BUCKET_NAME)
        real_s3.put_object(Bucket=BUCKET_NAME, Key="uploads/multi.jpg", Body=TINY_PNG)

        real_dynamo = boto3.resource("dynamodb", region_name="us-east-1")
        real_dynamo.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "imageId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "imageId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        mock_rek = MagicMock()
        mock_rek.detect_moderation_labels.return_value = {
            "ModerationLabels": [
                {"Name": "Violence", "Confidence": 90.0, "ParentName": ""},
                {"Name": "Nudity", "Confidence": 85.0, "ParentName": ""},
            ]
        }

        import lambdas.process_image as mod

        mod.s3_client = real_s3
        mod.rekognition_client = mock_rek
        mod.dynamodb = real_dynamo

        event = make_s3_event(BUCKET_NAME, "uploads/multi.jpg")
        result = mod.lambda_handler(event, None)

        assert result["statusCode"] == 403
        assert "Violence" in result["body"]
        assert "Nudity" in result["body"]
