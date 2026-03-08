import json
import boto3
import os
import uuid

s3_client = boto3.client('s3')

ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


def lambda_handler(event, context):
    """Generate a pre-signed S3 URL for uploading images"""
    try:
        bucket = os.environ['S3_BUCKET']
        params = event.get('queryStringParameters') or {}
        filename = params.get('filename')
        content_type = params.get('contentType', 'image/jpeg')

        if not filename:
            return response(400, {'error': 'filename required'})

        if content_type not in ALLOWED_TYPES:
            return response(400, {'error': f'Invalid content type. Allowed: {ALLOWED_TYPES}'})

        unique_key = f"uploads/{uuid.uuid4()}-{filename}"

        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket,
                'Key': unique_key,
                'ContentType': content_type
            },
            ExpiresIn=900
        )

        return response(200, {'uploadUrl': upload_url, 'key': unique_key})

    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': 'Failed to generate upload URL'})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }
