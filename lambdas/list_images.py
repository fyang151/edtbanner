import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')


def lambda_handler(event, context):
    """List all processed images from DynamoDB"""
    try:
        table_name = os.environ['DYNAMODB_TABLE']
        bucket = os.environ['S3_BUCKET']
        table = dynamodb.Table(table_name)

        # Scan all images (fine for small datasets)
        result = table.scan()
        items = result.get('Items', [])

        # Sort by timestamp (newest first)
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Build image URLs
        images = []
        for item in items:
            s3_key = item.get('s3Key')
            if not s3_key:
                continue

            image_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=3600
            )

            images.append({
                'imageId': item.get('imageId'),
                'filename': item.get('filename'),
                'url': image_url,
                'timestamp': item.get('timestamp')
            })

        return response_ok({'images': images, 'count': len(images)})

    except Exception as e:
        print(f"Error listing images: {str(e)}")
        return response_ok({'error': 'Failed to list images', 'images': []})


def response_ok(body):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }
