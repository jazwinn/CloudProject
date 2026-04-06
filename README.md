# CloudGraph

An interactive, Obsidian-style force-directed knowledge graph for photo memories. Photos are uploaded, processed by AWS Lambda, and rendered as a physics-based graph where nodes cluster dynamically by **location**, **time period**, and **people**.

![React](https://img.shields.io/badge/React-19-blue) ![Vite](https://img.shields.io/badge/Vite-8-purple)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Frontend](#frontend)
3. [Backend](#backend)
   - [Architecture](#architecture)
   - [API Endpoints](#api-endpoints)
   - [Database Schema](#database-schema)
   - [Authentication](#authentication)
   - [Lambda Functions](#lambda-functions)
   - [Project Structure](#project-structure)
4. [Full AWS Deployment Guide](#full-aws-deployment-guide)
   - [Phase 1: Security & Infrastructure](#phase-1-security--infrastructure)
   - [Phase 2: Backend & Lambdas](#phase-2-backend--lambdas-ec2)
   - [Phase 3: React Frontend](#phase-3-react-frontend-aws-amplify)

---

## Project Overview

CloudGraph is a full-stack cloud application with two main parts:

- **FrontEnd** — a React/Vite app that renders photos as an interactive force-directed graph with dynamic clustering, smooth animations, and a dark cinematic aesthetic inspired by Obsidian's graph view.
- **BackEnd** — a FastAPI server backed by AWS (S3, Lambda, Cognito, RDS PostgreSQL) that handles authenticated uploads, EXIF extraction, thumbnail generation, graph relationship building, and DBSCAN clustering.

---

## Frontend

### Features
- Force-directed graph with physics-based node simulation
- Dynamic clustering — switch between Location, Timeline, and People filters
- Hover interactions — tooltips reveal photo metadata and highlight connections
- Smooth animations when switching cluster modes
- Canvas rendering for 120+ nodes at 60fps
- Dark, cinematic aesthetic

### Getting Started

```bash
cd FrontEnd
npm install
npm run dev        # Dev server at http://localhost:3000
npm run build      # Production build → dist/
npm run preview    # Preview production build locally
```

### Structure

```
FrontEnd/src/
├── main.jsx                    # Entry point
├── App.jsx                     # Root component
├── index.css                   # Global styles & CSS variables
├── components/
│   ├── GraphCanvas.jsx         # Main canvas + render loop
│   ├── FilterBar.jsx           # Filter toggle buttons
│   ├── Legend.jsx              # Cluster color legend
│   ├── Tooltip.jsx             # Hover tooltip
│   └── StatsPanel.jsx          # Photo/connection/cluster counts
├── data/
│   └── photos.js               # Sample data generation
└── hooks/
    └── useForceSimulation.js   # Force-directed physics engine
```

### Customization
- **Photo count**: Change the argument in `generatePhotos(120)` inside `GraphCanvas.jsx`
- **Cluster categories**: Edit `locations`, `timePeriods`, and `people` arrays in `src/data/photos.js`
- **Colors**: Modify CSS variables in `src/index.css` or cluster color values in `photos.js`
- **Physics**: Tune repulsion, spring, and damping constants in `useForceSimulation.js`

---

## Backend

A FastAPI backend handling authenticated photo uploads, automated EXIF extraction, thumbnail generation, graph relationship building, and DBSCAN-based photo clustering — running on a serverless AWS architecture with a PostgreSQL database.

### Architecture

```mermaid
graph TD
    Client["Client"] -->|"Requests"| API["FastAPI (EC2 Auto Scaling)"]

    %% Upload Flow
    API -->|"POST /api/upload"| S3["S3 Bucket (uploads/)"]
    S3 -->|"S3 ObjectCreated"| SNS["SNS Topic"]
    SNS -->|"triggers"| SQS["SQS Queue (cloudgraph-image-processing)"]
    SQS -->|"processes"| ImageProc["image_processor<br>(EXIF → SQL DB)"]
    SQS -->|"processes"| ThumbGen["thumbnail_generator<br>(300x300 JPEG → S3)"]

    %% Batch Presign
    API -->|"POST /api/upload/batch-presign"| Presign["Presigned S3 PUT URLs"]
    Presign -.->|"Client uploads directly"| S3

    %% Graph Flow
    API -->|"GET /api/graph"| DB["SQL DB"]
    DB -->|"Haversine + time comparison"| GraphJSON["D3-ready JSON"]

    %% Clusters Flow
    API -->|"GET /api/clusters"| DB
    DB -->|"DBSCAN (Background task)"| Clusters["Cluster labels + geocoding"]
    Clusters -.->|"Caches result"| DB
```

**AWS services used:** S3, SNS, SQS, Lambda, Cognito, RDS (PostgreSQL)

---

### API Endpoints

#### `GET /health`
Simple liveness check.
```json
{ "status": "ok" }
```

---

#### `POST /api/upload`
Upload a single photo. The file is stored in S3 under `uploads/{user_id}/{uuid}.ext`. Lambda functions automatically handle EXIF extraction and thumbnail generation in the background via the SQS queue.

**Auth:** `Authorization: Bearer <cognito_token>`
**Body:** `multipart/form-data` — `file` field (JPEG, PNG, or HEIC)

```json
{
  "file_key": "uploads/user-sub/uuid.jpg",
  "presigned_url": "https://s3.amazonaws.com/...",
  "message": "Upload successful. Background processing initiated."
}
```
The `presigned_url` is valid for **15 minutes**.

---

#### `POST /api/upload/batch-presign`
Generate presigned S3 PUT URLs for a batch of up to 500 files. The client uploads directly to S3 in parallel — no file data passes through the API server. See [bulkUpload.js](#bulk-upload) for the frontend utility.

**Auth:** `Authorization: Bearer <cognito_token>`
**Body:** `application/json`

```json
{ "files": [{ "filename": "photo1.jpg", "content_type": "image/jpeg" }] }
```

```json
{
  "uploads": [
    { "filename": "photo1.jpg", "file_key": "uploads/.../uuid.jpg", "presigned_url": "https://..." }
  ]
}
```
Each presigned URL is scoped to exactly `uploads/{user_id}/{uuid}.ext` with a **15-minute TTL**.

---

#### `GET /api/graph`
Returns a graph of relationships between the user's photos based on time and geographic proximity. Designed to feed directly into D3.js or Cytoscape.

**Auth:** `Authorization: Bearer <cognito_token>`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `time_threshold_minutes` | `60` | Max time gap (minutes) to create a time edge |
| `distance_threshold_km` | `1.0` | Max distance (km) to create a location edge |

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

#### `GET /api/clusters`
Groups the user's photos into clusters using a pure Python DBSCAN implementation. Clusters are labelled with a human-readable date and city name (e.g. `2023-10-12 · Paris`) via Nominatim geocoding.

For larger libraries, clustering runs directly in the backend EC2 server and the result is cached in the database. Requests within 10 minutes of a completed run return the cached result instantly.

**Auth:** `Authorization: Bearer <cognito_token>`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mode` | `"combined"` | `"time"`, `"location"`, or `"combined"` |
| `time_eps_minutes` | `60` | DBSCAN epsilon for time axis (minutes) |
| `distance_eps_km` | `1.0` | DBSCAN epsilon for location axis (km) |
| `min_samples` | `2` | Minimum photos to form a cluster |

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

---

### Database Schema

Tables are created by running `python BackEnd/scripts/setup_database.py` once.

#### `image_metadata`

| Column | Type | Description |
|--------|------|-------------|
| `image_id` | VARCHAR (PK) | S3 object key |
| `user_id` | VARCHAR | Cognito user `sub` |
| `uploaded_at` | VARCHAR | ISO 8601 upload timestamp |
| `date_taken` | VARCHAR (nullable) | ISO 8601 date from EXIF |
| `gps_lat` | FLOAT (nullable) | Latitude from EXIF GPS |
| `gps_lon` | FLOAT (nullable) | Longitude from EXIF GPS |
| `thumbnail_key` | VARCHAR (nullable) | S3 key of the generated thumbnail |
| `status` | VARCHAR | Processing state: `pending` → `processed` |

#### `cluster_results`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-incrementing ID |
| `user_id` | VARCHAR | Cognito user `sub` |
| `computed_at` | VARCHAR | ISO 8601 timestamp of when clustering ran |
| `mode` | VARCHAR | Clustering mode used |
| `result` | TEXT | Full cluster result serialised as JSON |

---

### Authentication

All endpoints (except `/health`) require a Cognito JWT in the `Authorization: Bearer <token>` header. The `get_current_user` dependency validates the token by fetching the JWKS from Cognito's `.well-known` endpoint, verifying the RS256 signature, and returning the user's `sub` as their unique ID. Both `id` tokens and `access` tokens are supported.

---

### Lambda Functions

| Function | Trigger | Responsibility |
|----------|---------|----------------|
| `image_processor.py` | `s3:ObjectCreated:*` on `uploads/` | Extracts EXIF date + GPS and writes to `image_metadata` |
| `thumbnail_generator.py` | `s3:ObjectCreated:*` on `uploads/` | Generates a 300×300 JPEG thumbnail, uploads to `thumbnails/`, updates `thumbnail_key` |

---

### Project Structure

```
BackEnd/
├── main.py                        # FastAPI app, CORS, router registration
├── config.py                      # Pydantic settings (loaded from .env)
├── Dockerfile
├── requirements.txt
├── .env.example
├── auth/
│   └── cognito.py                 # JWT verification dependency
├── routers/
│   ├── upload.py                  # POST /api/upload
│   ├── graph.py                   # GET /api/graph
│   └── clusters.py                # GET /api/clusters
├── services/
│   ├── database.py                # SQLAlchemy engine, models, session context
│   ├── metadata_service.py        # save_image_metadata() (writes to PostgreSQL)
│   ├── s3_service.py              # S3 upload + presigned URL generation
│   ├── lambda_service.py          # invoke_clustering_lambda()
│   ├── graph_service.py           # build_graph() — Haversine + time edge logic
│   ├── clustering_service.py      # compute_clusters() — pure Python DBSCAN
│   └── exif_service.py            # extract_exif_metadata() — piexif + Pillow
├── lambda/
│   ├── image_processor.py         # S3-triggered EXIF extraction
│   └── thumbnail_generator.py     # S3-triggered thumbnail generation
├── scripts/
│   ├── setup_database.py          # Creates SQL tables manually (optional)
│   └── deploy_lambda.py           # Python script to package and deploy Lambdas
└── utils/
    ├── geo.py                     # Haversine distance formula
    └── geocode.py                 # Nominatim reverse geocoding
```

---

## Full AWS Deployment Guide

### Phase 1: Security & Infrastructure

#### 1. Amazon Cognito (Authentication)
1. Open the **AWS Cognito Console** → **Create user pool**
2. Select **Email** as the sign-in attribute
3. In the **App Integration** step, create a **Public client** (no client secret)
4. Note down your **User Pool ID** and **App Client ID**

#### 2. Amazon S3 (Photo Storage)
1. Open the **AWS S3 Console** → **Create bucket**
2. Name it uniquely (e.g. `cloudgraph-uploads-xyz`)
3. Leave Block Public Access **ON** — the backend generates presigned URLs, so the bucket does not need to be public
4. Enable **CORS** in the bucket permissions to allow your frontend domain to read files

#### 3. Amazon RDS (PostgreSQL Database)
1. Open the **AWS RDS Console** → **Create database**
2. Select **PostgreSQL** as the engine (or **Aurora PostgreSQL** for production)
3. Choose a `db.t3.micro` instance for development
4. Note down your **endpoint**, **port**, **username**, and **password**
5. Make sure its **Security Group** allows inbound connections on port `5432` from **both** your ECS task security group AND your local computer's IP address (so you can run the table creation script locally).

#### 4. Amazon SNS & SQS (Upload Buffering)
1. Open the **AWS SNS Console** → **Create topic** (Standard). Name it `cloudgraph-uploads-topic`.
2. Open the **AWS SQS Console** → **Create queue**. Name it `cloudgraph-image-processing-dlq`.
3. Create another queue named `cloudgraph-image-processing` (Visibility timeout: 300s). For the **Redrive policy**, select your DLQ and set Maximum receives to 3.
4. Subscribe the `cloudgraph-image-processing` queue to the `cloudgraph-uploads-topic` SNS topic.
5. In the **AWS S3 Console**, go to your bucket → **Properties** → **Event notifications**. Create an event for `s3:ObjectCreated:*` with prefix `uploads/` and select your SNS topic as the destination.

---

### Phase 2: Backend & Lambdas (EC2 Auto Scaling)

#### 1. Serverless Lambda Workers
1. Create **2 empty Lambda functions** in the AWS Console: `thumbnail_generator` and `image_processor`. Choose **Python 3.10+**.
2. **Execution Role:** If you are on a Student Account (AWS Academy/Vocareum), select the existing **`LabRole`**. Do NOT try to create a new role, as your permissions are likely restricted.
3. In the AWS Lambda Console for each function, click **Upload from > .zip file**. Use the files in `BackEnd/deploy_zips/`.
4. On the function pages for `image_processor` and `thumbnail_generator`, click **Add trigger** → select **SQS**, point it to `cloudgraph-image-processing`.

#### 2. FastAPI Core Server (EC2 Auto Scaling Group)

1. **IAM Role:** If you are on a Student Account, select the existing **`LabRole`** (or `LabInstanceProfile`) when configuring the Launch Template. This role already has the necessary permissions for S3, RDS, and CloudWatch.
2. **Target Group:** Create a Target Group (Type: Instance, Port: 8000). Set the health check path to `/health`.
3. **Load Balancer:** Create an Application Load Balancer (ALB) and add a listener on port 80 (or 443) that forwards to your Target Group.
4. **Launch Template:** Create a Launch Template for your EC2 instances:
   - **AMI:** Ubuntu 22.04 LTS.
   - **Instance Type:** `t3.micro` or similar.
   - **User Data:** Paste the contents of `BackEnd/scripts/setup_ec2.sh`. Update the placeholders (`REPO_URL`, `DATABASE_URL`, etc.) with your actual values.
5. **Auto Scaling Group (ASG):** Create an ASG using your Launch Template:
   - Select your VPC and subnets.
   - Attach it to the existing Load Balancer / Target Group.
   - Set **Desired capacity** to 1, **Minimum** to 1, and **Maximum** to 10.
6. **Scaling Policy:** In the ASG **Automatic scaling** tab, add a **Target tracking scaling policy**:
   - **Metric type:** Average CPU utilization.
   - **Target value:** 60.
   - **Instances need:** 300 seconds to warm up.

#### 3. Database Migration

**Good news!** The API now includes **auto-migration logic**. As soon as your first EC2 instance starts up and connects to the RDS database, it will automatically create the necessary `image_metadata` and `cluster_results` tables for you.

You do **not** need to run any scripts locally if you cannot connect to the database from your computer. Just ensure your `DATABASE_URL` environment variable is correct in your Launch Template's User Data.

---

## Security Architecture

The application uses **Amazon Cognito** for authentication. All API calls (except `/health`) require a valid JWT token.

- **Authentication:** Verified via Cognito's JWKS endpoint.
- **Data Isolation:** Enforced at the application level by filtering all database queries by the authenticated `user_id`.
- **S3 Access:** Secured via 15-minute **Presigned URLs**. The API ensures that users can only get or put objects within their own `uploads/{user_id}/` folder.

---

## Bulk Upload Made Easy

CloudGraph handles batches of up to **500 images** at once using a high-performance "direct-to-S3" strategy. This means your images bypass the API server, preventing bottlenecks and timeouts.

### How to use Bulk Upload:

1.  **Select Files:** In the frontend UI, select multiple images (JPEG, PNG, or HEIC).
2.  **Get Permission:** The frontend calls `POST /api/upload/batch-presign` with the list of filenames. The backend returns a set of unique, short-lived S3 upload URLs.
3.  **Parallel Upload:** The frontend utility (`bulkUpload.js`) automatically uploads your files directly to S3 in parallel batches.
4.  **Background Processing:** As soon as an image hits S3, AWS SQS triggers the **Image Processor** (for EXIF extraction) and **Thumbnail Generator** (for 300x300 previews).
5.  **Done!** Your graph will update automatically as processing finishes.

> [!TIP]
> The bulk upload utility uses `Promise.allSettled`, so if one file fails during a massive batch, the rest will continue successfully.

---

### Phase 3: React Frontend (AWS Amplify)

#### 1. Update the API Base URL
In `FrontEnd/src/api.js`, point the app at your live EC2 backend:
```javascript
export const API_BASE = 'https://YOUR-ALB-DNS-NAME/api';
```

#### 2. Deploy to AWS Amplify
1. Push your updated code to GitHub
2. Open the **AWS Amplify Console** → **Host Web App**
3. Connect your GitHub repository and select your branch
4. Amplify auto-detects Vite and uses `npm run build` to compile the static assets
5. Click **Save and Deploy**

Amplify will provide a live URL (e.g. `https://main.xyz.amplifyapp.com`). Navigate there, authenticate with a Cognito token, and your photos will upload, trigger the Lambda processors, and render to the D3 graph entirely in the cloud.

---

## 📚 API Guide Notebook
An interactive `BackEnd/api_guide.ipynb` Jupyter notebook is included for testing and debugging all endpoints locally using Python HTTP calls.
