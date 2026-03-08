hi claude!!!!!!

# Hackathon Banner

Serverless image banner app: S3 + Lambda + API Gateway + DynamoDB + Rekognition.

## Routes
- `POST /api/upload-url` → getUploadUrl Lambda (pre-signed S3 URL)
- `GET /api/images` → listImages Lambda (returns image list from DynamoDB)

## Upload Flow
1. Frontend calls `POST /api/upload-url` → gets pre-signed URL
2. Frontend uploads directly to S3 (`uploads/` prefix)
3. S3 triggers processImage Lambda
4. Rekognition checks content (threshold: 75%). Flagged → delete. Clean → move to `processed/`, write metadata to DynamoDB.
5. Frontend polls `GET /api/images`

## TODO
### Done
- [x] Lambdas: getUploadUrl, processImage, listImages
- [x] Terraform: S3, DynamoDB, IAM, Lambda, API Gateway, S3 trigger
- [x] Unit tests (moto + MagicMock for Rekognition)

### Remaining
- [ ] Frontend: HTML/CSS/JS banner + upload form + polling
- [ ] `terraform apply` + end-to-end smoke test

## Testing
```bash
pip install -r requirements-test.txt
pytest -v
```
- Uses `moto` for S3/DynamoDB, `MagicMock` for Rekognition
- No real AWS needed, no image files needed
