# CloudGraph: Full AWS Deployment Guide

This guide covers how to deploy the entire CloudGraph application—both the React frontend and the FastAPI backend—completely to AWS for a production-ready environment.

---

## Phase 1: Security & Database Provisioning

### 1. Amazon Cognito (Authentication)
Before anything else, you need a Cognito User Pool to generate the JWT tokens that lock down your graph API.
1. Go to the **AWS Cognito Console** and click **Create user pool**.
2. Select **Email** as the sign-in attribute.
3. Configure password requirements as desired.
4. Skip MFA for development, or require it for production.
5. In the **App Integration** step, create a **Public client** (do not generate a client secret). 
6. Create the pool. Note down your **User Pool ID** and **Client ID**.

### 2. Amazon S3 (Photo Storage)
1. Go to the **AWS S3 Console** and click **Create bucket**.
2. Name it uniquely (e.g., `cloudgraph-uploads-xyz`). 
3. Leave Block Public Access **ON**—the backend generates secure pre-signed URLs, so the bucket itself does not need to be public.
4. Enable **CORS** (Cross-Origin Resource Sharing) in the bucket permissions to allow your frontend URL to read/put files.

### 3. DynamoDB (Metadata & Caching)
Run our automated script from your local `BackEnd` folder to instantly provision the `ImageMetadata` and `ClusterResults` tables:
```bash
cd BackEnd
python scripts/setup_lambda_triggers.py
```

---

## Phase 2: Deploying the Backend API & Lambdas

Your `BackEnd` directory contains two architectures: the live FastAPI endpoints and the asynchronous AWS Lambda workers.

### 1. Serverless Lambda Workers
Our background processors (thumbnails, EXIF extraction, and ML clustering) run on Lambda to keep your UI lightning fast.
1. **Create 3 empty Lambda functions** in the AWS Console matching exactly these names: `thumbnail_generator`, `image_processor`, and `clustering_processor`. Choose **Python 3.10+** as the runtime.
2. Give their IAM Execution Roles permission to read/write to S3 and DynamoDB.
3. Deploy the code from your local machine using our script:
```bash
cd BackEnd
chmod +x scripts/deploy_lambda.sh
./scripts/deploy_lambda.sh
```
4. **Wire the S3 Triggers**: Go back to your S3 Bucket properties -> **Event Notifications**. Create a new event for `s3:ObjectCreated:*` with the prefix `uploads/`, and select your `thumbnail_generator` and `image_processor` Lambdas as the destinations.

### 2. FastAPI Core Server (Amazon EC2)
The main API Server (which serves `/upload`, `/graph`, `/clusters`) needs to be hosted 24/7. **Amazon EC2** is the best option for AWS Academy environments.
1. Go to the AWS EC2 Console and launch a new **Ubuntu 22.04 LTS** instance (t2.micro is fine).
2. Under **Network settings**, choose "Select existing security group" or create a new one. Add an **Inbound Rule** for `Custom TCP`, Port Range `8000`, Source `Anywhere-IPv4`.
3. SSH into your instance using EC2 Instance Connect or your `.pem` key.
4. Run the following commands to install dependencies and pull your code:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y
git clone https://github.com/YOUR_GITHUB_USERNAME/CloudProject.git
cd CloudProject/BackEnd
pip install -r requirements.txt
```
5. Create your environment file:
```bash
nano .env
```
Paste your production variables into it (AWS keys, Academy session token, Cognito IDs) and save (`Ctrl+O`, `Enter`, `Ctrl+X`).
6. Run the server permanently in the background using `nohup`:
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```
7. Note down your EC2 instance's **Public IPv4 address**. Your API is now live at `http://YOUR-EC2-IP:8000/api`.

---

## Phase 3: Deploying the React Frontend

Now that your backend URL is live, it's time to host the web interface. **AWS Amplify** is the recommended standard for hosting React/Vite apps.

### 1. Update API References
In your `FrontEnd/src/api.js` file, change the `API_BASE` from localhost to your new live backend URL:
```javascript
// Change this:
// export const API_BASE = 'http://localhost:8000/api';

// To your live AWS App Runner / Backend URL:
export const API_BASE = 'https://YOUR-APP-RUNNER-URL.awsapprunner.com/api';
```

### 2. Connect to AWS Amplify
1. Push your updated `FrontEnd/` folder to GitHub.
2. Open the **AWS Amplify Console** and click **Host Web App**.
3. Connect your GitHub repository and select your branch.
4. Amplify will automatically detect that it's a Vite project. It will use `npm run build` to compile the static assets.
5. Click **Save and Deploy**.

### 3. Final Integration Test
Amplify will provide you with a live frontend URL (e.g., `https://main.xyz.amplifyapp.com`). 
Navigate to that URL, paste a generated Cognito token into your new Data Panel, and watch your photos upload, trigger the asynchronous AWS Lambdas, and render to the D3 graph entirely in the cloud!
