import json
import boto3
import os
from datetime import datetime, timezone
import uuid

s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    """
    Process uploaded image: check moderation, save metadata.
    Triggered by S3 upload event.
    """
    try:
        table_name = os.environ['DYNAMODB_TABLE']
        table = dynamodb.Table(table_name)

        # Parse S3 event
        s3_info = event['Records'][0]['s3']
        bucket = s3_info['bucket']['name']
        key = s3_info['object']['key']

        # Skip if already processed
        if key.startswith('processed/'):
            print(f"Skipping already processed: {key}")
            return {'statusCode': 200, 'body': 'Already processed'}

        print(f"Processing: s3://{bucket}/{key}")

        # 1. Check with Rekognition for inappropriate content
        print("Checking image with Rekognition...")
        moderation = rekognition_client.detect_moderation_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MinConfidence=75
        )

        if moderation['ModerationLabels']:
            labels = [label['Name'] for label in moderation['ModerationLabels']]
            print(f"Image rejected: {labels}")
            s3_client.delete_object(Bucket=bucket, Key=key)
            return {'statusCode': 403, 'body': f'Content flagged: {labels}'}

        print("Image passed moderation")

        # 2. Move to processed folder
        filename = os.path.basename(key)
        processed_key = f"processed/{filename}"

        s3_client.copy_object(
            Bucket=bucket,
            CopySource=f'{bucket}/{key}',
            Key=processed_key
        )

        # Delete original from uploads/
        s3_client.delete_object(Bucket=bucket, Key=key)

        print(f"Moved to: {processed_key}")

        # 3. Save metadata to DynamoDB
        image_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        table.put_item(
            Item={
                'imageId': image_id,
                'filename': filename,
                's3Key': processed_key,
                'timestamp': timestamp
            }
        )

        print(f"Saved metadata: {image_id}")

        return {'statusCode': 200, 'body': json.dumps({'imageId': image_id})}

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return {'statusCode': 500, 'body': str(e)}
