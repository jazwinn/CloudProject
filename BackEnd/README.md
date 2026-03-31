# CloudGraph Backend API

A complete FastAPI-driven serverless architecture built on AWS to handle high-performance photo uploading, processing, DBSCAN clustering, and graph relationship building.

## Core Features
1. **S3 Uploads & Auth**: Lightning-fast `POST /api/upload` endpoint secured by Amazon Cognito JWTs. The file is mapped directly to an S3 object yielding an instant 1-hour presigned URL.
2. **Serverless Image Processing (AWS Lambda)**:
   - S3 triggers independently run `thumbnail_generator.py` converting payloads to standard 300x300 bounding boxes using the `Pillow` library.
   - S3 triggers run `image_processor.py` extracting EXIF data in the background and writing records to the SQL database.
3. **Graph Relationships (`GET /api/graph`)**: Instantly resolves geographical overlaps via Haversine mappings and chronological overlap clustering in a format ready for visualization engines like D3.js or Cytoscape.
4. **DBSCAN ML Clustering (`GET /api/clusters`)**: Group photos effectively. Incorporates Nominatim free geocoding to automatically brand clusters (e.g., `2023-10-12 · Paris`). When users hold an image library over a threshold, the backend automatically transitions to invoke `clustering_processor.py` on AWS Lambda, decoupling and caching the resulting arrays in the `cluster_results` SQL table.

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
AWS_LAMBDA_FUNCTION_NAME="cloudgraph-cluster-processor"

# PostgreSQL connection string
DATABASE_URL="postgresql://user:password@localhost:5432/cloudgraph"

COGNITO_REGION="us-east-1"
COGNITO_USER_POOL_ID="us-east-1_xxxxx"
COGNITO_APP_CLIENT_ID="xxxxxxxxx"
```

### 3. Provision the Database
Run the setup script once to create the `image_metadata` and `cluster_results` tables in your SQL database:
```bash
python scripts/setup_database.py
```

### 4. Configure Lambda Triggers
Run the following script to print the S3 trigger configuration you'll need to apply manually in the AWS Console:
```bash
python scripts/setup_lambda_triggers.py
```
*Note: Read the console output. You'll need to manually link your `s3:ObjectCreated:*` triggers within the AWS Dashboard connecting to your `thumbnail_generator` and `image_processor` Lambdas.*

### 5. Deploy the Lambda Engine
Zip and upload the Lambda functions using the provided shell script:
```bash
chmod +x scripts/deploy_lambda.sh
./scripts/deploy_lambda.sh
```

### 6. Run the Local FastAPI Server
Launch the API locally:
```bash
uvicorn main:app --reload
```

---

## 📚 API Guide Notebook
If you want to debug the application on your machine via Python HTTP scripts, utilize the provided **Jupyter Notebook**:
`api_guide.ipynb`
