# CloudGraph Backend API

A complete FastAPI-driven serverless architecture built on AWS to handle high-performance photo uploading, processing, DBSCAN clustering, and graph relationship building.

## Core Features
1. **S3 Uploads & Auth**: Lightning-fast `POST /api/upload` endpoint secured by Amazon Cognito JWTs. The file is mapped directly to an S3 object yielding an instant 1-hour presigned URL.
2. **Serverless Image Processing (AWS Lambda)**:
   - S3 triggers independently run `thumbnail_generator.py` converting payloads to standard 300x300 bounding boxes using the `Pillow` library.
   - S3 triggers run `image_processor.py` extracting EXIF data seamlessly in the background and logging records to DynamoDB.
3. **Graph Relationships (`GET /api/graph`)**: Instantly resolves geographical overlaps via Haversine mappings and chronological overlap clustering in a format ready for visualization engines like D3.js or Cytoscape.
4. **DBSCAN ML Clustering (`GET /api/clusters`)**: Group photos effectively. Incorporates Nominatim free geocoding to automatically brand clusters (e.g., `2023-10-12 · Paris`). When users hold an image boundary > 50, the backend automatically transitions to invoke `clustering_processor.py` on AWS Lambda, decoupling and caching the resulting arrays inside the `ClusterResults` table naturally.

---

## 🛠 Deployment & Local Setup

### 1. Requirements
Ensure you have Python 3.10+ and an AWS Account configured via `aws configure` locally.

```bash
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
Create a `.env` file at the root of `BackEnd/` extending `.env.example`:
```env
AWS_REGION="us-east-1"
S3_BUCKET_NAME="cloudgraph-uploads"
DYNAMO_TABLE_NAME="ImageMetadata"
AWS_LAMBDA_FUNCTION_NAME="cloudgraph-cluster-processor"

COGNITO_REGION="us-east-1"
COGNITO_USER_POOL_ID="us-east-1_xxxxx"
COGNITO_APP_CLIENT_ID="xxxxxxxxx"
```

### 3. Provision the Database
We have included an automated script configuring the `ImageMetadata` and `ClusterResults` tables out of the box equipped for `PAY_PER_REQUEST` metrics on AWS:
```bash
python scripts/setup_lambda_triggers.py
```
*Note: Read the console output. You'll need to manually link your `s3:ObjectCreated:*` triggers within the AWS Dashboard connecting to your `thumbnail` and `processor` Lambdas.*

### 4. Deploy the Lambda Engine
You can zip and upload your current backend scripts securely mapped directly upwards using the shell script:
```bash
chmod +x scripts/deploy_lambda.sh
./scripts/deploy_lambda.sh
```

### 5. Run the Local FastAPI Server
Launch your API routing locally:
```bash
uvicorn main:app --reload
```

---

## 📚 API Guide Notebook
If you want to debug the application natively on your machine interacting securely via Python HTTP scripts, utilize the provided locally hosted **Jupyter Notebook**:
`api_guide.ipynb`
