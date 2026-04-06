# CloudGraph Backend API

A FastAPI backend powering the CloudGraph photo management platform. Handles authenticated photo uploads, automated EXIF extraction, thumbnail generation, graph relationship building, and DBSCAN-based photo clustering — all running on a serverless AWS architecture with a PostgreSQL database.

---

## Architecture Overview

```
Client
  │
  ▼
FastAPI (EC2 Auto Scaling)
  │
  ├── POST /api/upload ──────► S3 Bucket (uploads/{user_id}/{uuid}.ext)
  │                                  │
  │                          S3 ObjectCreated event (via SQS/SNS)
  │                          ┌───────┴────────┐
  │                          ▼                ▼
  │                 image_processor.py   thumbnail_generator.py
  │                 (EXIF → SQL DB)      (300x300 JPEG → S3)
  │
  ├── GET /api/graph ────────► SQL DB → Haversine + time comparison → D3-ready JSON
  │
  └── GET /api/clusters ─────► SQL DB → DBSCAN → cluster labels + geocoding
                                    └── Background task → SQL cache
```

**AWS services used:** S3, Lambda, Cognito, RDS (PostgreSQL)

---

## API Endpoints

### `GET /health`
Simple liveness check.

**Response:**
```json
{ "status": "ok" }
```

---

### `POST /api/upload`
Upload a photo. Requires a valid Cognito Bearer token. The file is stored in S3 and background Lambda functions handle EXIF extraction and thumbnail generation automatically.

**Auth:** `Authorization: Bearer <cognito_token>`

**Body:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | JPEG, PNG, or HEIC image |

**Response:**
```json
{
  "file_key": "uploads/user-sub/uuid.jpg",
  "presigned_url": "https://s3.amazonaws.com/...",
  "message": "Upload successful. Background processing initiated."
}
```
The `presigned_url` is valid for 1 hour and can be used to retrieve the image directly from S3.

---

### `GET /api/graph`
Returns a graph of relationships between the authenticated user's photos, based on time proximity and/or geographic proximity. Designed to feed directly into D3.js or Cytoscape.

**Auth:** `Authorization: Bearer <cognito_token>`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `time_threshold_minutes` | int | `60` | Max time gap (in minutes) between two photos to create a time edge |
| `distance_threshold_km` | float | `1.0` | Max distance (in km) between two photos to create a location edge |

**Response:**
```json
{
  "nodes": [
    { "id": "uploads/user/uuid.jpg", "date_taken": "2023-10-12T14:30:00", "gps_lat": 48.8566, "gps_lon": 2.3522 }
  ],
  "edges": [
    { "source": "uploads/user/uuid1.jpg", "target": "uploads/user/uuid2.jpg", "relationship": "time+location" }
  ]
}
```
Edge `relationship` values: `"time"`, `"location"`, or `"time+location"`.

---

### `GET /api/clusters`
Groups the authenticated user's photos into clusters using a pure Python DBSCAN implementation. Clusters are labelled with a human-readable date and city name (e.g. `2023-10-12 · Paris`) using Nominatim geocoding.

For larger libraries, clustering is processed directly in the FastAPI backend on the EC2 instance, and the result is cached in the database. Subsequent requests within 10 minutes return the cached result instantly.

**Auth:** `Authorization: Bearer <cognito_token>`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | string | `"combined"` | Clustering mode: `"time"`, `"location"`, or `"combined"` |
| `time_eps_minutes` | int | `60` | DBSCAN epsilon for time axis (minutes) |
| `distance_eps_km` | float | `1.0` | DBSCAN epsilon for location axis (kilometers) |
| `min_samples` | int | `2` | Minimum photos required to form a cluster |

**Response (clusters ready):**
```json
{
  "clusters": [
    {
      "cluster_id": "uuid",
      "label": "2023-10-12 · Paris",
      "photo_ids": ["uploads/user/uuid1.jpg", "uploads/user/uuid2.jpg"],
      "centroid_lat": 48.8566,
      "centroid_lon": 2.3522
    }
  ],
  "unclustered": ["uploads/user/uuid3.jpg"]
}
```

**Response (processing asynchronously):**
```json
{
  "status": "processing",
  "message": "Clustering started, check back in a few seconds"
}
```

---

## Database Schema

The application uses PostgreSQL (via SQLAlchemy). Tables are created by running `scripts/setup_database.py`.

### `image_metadata`
Stores photo metadata extracted from EXIF data on upload.

| Column | Type | Description |
|--------|------|-------------|
| `image_id` | VARCHAR (PK) | S3 object key (e.g. `uploads/user/uuid.jpg`) |
| `user_id` | VARCHAR | Cognito user `sub` |
| `uploaded_at` | VARCHAR | ISO 8601 upload timestamp |
| `date_taken` | VARCHAR (nullable) | ISO 8601 date from EXIF, if present |
| `gps_lat` | FLOAT (nullable) | Latitude from EXIF GPS, if present |
| `gps_lon` | FLOAT (nullable) | Longitude from EXIF GPS, if present |
| `thumbnail_key` | VARCHAR (nullable) | S3 key of the generated thumbnail |

### `cluster_results`
Cache table for DBSCAN results produced by the backend.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-incrementing ID |
| `user_id` | VARCHAR | Cognito user `sub` |
| `computed_at` | VARCHAR | ISO 8601 timestamp of when clustering ran |
| `mode` | VARCHAR | Clustering mode (`time`, `location`, `combined`) |
| `result` | TEXT | Full cluster result serialised as JSON |

---

## Authentication

All API endpoints (except `/health`) require a valid **Amazon Cognito JWT** in the `Authorization: Bearer <token>` header.

The `get_current_user` dependency in `auth/cognito.py` validates the token by:
1. Fetching the JWKS from the Cognito `.well-known` endpoint
2. Matching the token `kid` header to the correct public key
3. Verifying the RS256 signature, issuer, and audience
4. Returning the user's `sub` claim as their unique `user_id`

Both `id` tokens and `access` tokens are supported.

---

## Lambda Functions

The two Lambdas live in the `lambda/` directory and share the same backend codebase via `sys.path`.

### `image_processor.py`
Triggered by `s3:ObjectCreated:*` on the `uploads/` prefix. Downloads the image from S3, runs `extract_exif_metadata()` to pull date and GPS coordinates from EXIF, then writes the result to the `image_metadata` SQL table.

### `thumbnail_generator.py`
Triggered by `s3:ObjectCreated:*` on the `uploads/` prefix. Generates a 300×300 JPEG thumbnail (letterboxed with a black background), uploads it to `thumbnails/{user_id}/{filename}` in S3, then updates the `thumbnail_key` column for the corresponding row in `image_metadata`.


---

## Project Structure

```
BackEnd/
├── main.py                        # FastAPI app, CORS, router registration
├── config.py                      # Pydantic settings (loaded from .env)
├── Dockerfile
├── requirements.txt
├── .env.example
│
├── auth/
│   └── cognito.py                 # JWT verification dependency
│
├── routers/
│   ├── upload.py                  # POST /api/upload
│   ├── graph.py                   # GET /api/graph
│   └── clusters.py                # GET /api/clusters
│
├── services/
│   ├── database.py                # SQLAlchemy engine, models, session context
│   ├── metadata_service.py        # save_image_metadata() (writes to PostgreSQL)
│   ├── s3_service.py              # upload_file_to_s3(), presigned URL generation
│   ├── lambda_service.py          # invoke_clustering_lambda()
│   ├── graph_service.py           # build_graph() — Haversine + time edge logic
│   ├── clustering_service.py      # compute_clusters() — pure Python DBSCAN
│   └── exif_service.py            # extract_exif_metadata() — piexif + Pillow
│
├── lambda/
│   ├── image_processor.py         # S3-triggered EXIF extraction
│   └── thumbnail_generator.py     # S3-triggered thumbnail generation
│
├── scripts/
│   ├── setup_database.py          # Creates SQL tables manually (optional)
│   ├── setup_ec2.sh               # User Data script for automated EC2 setup
│   └── deploy_lambda.py           # Python script to package and deploy Lambdas
│
└── utils/
    ├── geo.py                     # Haversine distance formula
    └── geocode.py                 # Nominatim reverse geocoding
```

---

## 🛠 Deployment & Local Setup

### 1. Requirements
Python 3.10+ and a configured AWS account.

```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file at the root of `BackEnd/` using `.env.example` as a template:

```env
# AWS credentials
AWS_ACCESS_KEY_ID="your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
AWS_SESSION_TOKEN="your_aws_academy_token_here"   # omit if using long-term credentials
AWS_REGION="us-east-1"

# S3
S3_BUCKET_NAME="cloudgraph-uploads"

# PostgreSQL (Amazon RDS or local)
DATABASE_URL="postgresql://user:password@localhost:5432/cloudgraph"

# Amazon Cognito
COGNITO_REGION="us-east-1"
COGNITO_USER_POOL_ID="us-east-1_xxxxx"
COGNITO_APP_CLIENT_ID="xxxxxxxxx"
```

### 3. Provision the Database
Run once to create the `image_metadata` and `cluster_results` tables (optional, as the API also auto-creates these on first startup):

```bash
python scripts/setup_database.py
```

### 4. Configure Lambda Triggers
In the AWS Console, navigate to your S3 bucket and attach `s3:ObjectCreated:*` triggers on the `uploads/` prefix. Send these events to the SQS queue that triggers the `image_processor` and `thumbnail_generator` Lambdas.

### 5. Deploy Lambda Functions
```bash
python scripts/deploy_lambda.py
```

### 6. Run the FastAPI Server (local)
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 7. Run with Docker
```bash
docker build -t cloudgraph-backend .
docker run -p 8000:8000 --env-file .env cloudgraph-backend
```

---

## 📚 API Guide Notebook
An interactive `api_guide.ipynb` Jupyter notebook is included for testing and debugging all endpoints locally using Python HTTP calls.
