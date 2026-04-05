import os
import shutil
import subprocess
import zipfile
import boto3
from pathlib import Path

# Configuration
LAMBDAS = ["thumbnail_generator", "image_processor", "clustering_processor"]
BASE_DIR = Path(__file__).parent.parent
LAMBDA_DIR = BASE_DIR / "lambda"
SERVICES_DIR = BASE_DIR / "services"
UTILS_DIR = BASE_DIR / "utils"
PACKAGE_DIR = BASE_DIR / "package"
REQ_FILE = BASE_DIR / "lambda_requirements.txt"
ENV_FILE = BASE_DIR / ".env"

ZIP_OUTPUT_DIR = BASE_DIR / "deploy_zips"

def get_s3_bucket():
    """Reads S3_BUCKET_NAME from .env file."""
    if not ENV_FILE.exists():
        return "cloudgraph-uploads"
    with open(ENV_FILE, "r") as f:
        for line in f:
            if line.startswith("S3_BUCKET_NAME="):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "cloudgraph-uploads"

def create_package():
    """Installs requirements into the package directory."""
    print("--- Installing dependencies ---")
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir()
    
    # Create output dir for zips if missing
    if not ZIP_OUTPUT_DIR.exists():
        ZIP_OUTPUT_DIR.mkdir()
    
    subprocess.check_call([
        "python", "-m", "pip", "install", 
        "-r", str(REQ_FILE), 
        "-t", str(PACKAGE_DIR)
    ])

def zip_lambda(lambda_name):
    """Creates a deployment zip for a specific lambda."""
    zip_path = ZIP_OUTPUT_DIR / f"{lambda_name}.zip"
    print(f"--- Packaging {lambda_name} -> {zip_path.name} ---")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add dependencies
        for root, dirs, files in os.walk(PACKAGE_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(PACKAGE_DIR)
                zf.write(full_path, rel_path)
        
        # 2. Add Lambda handler (at root)
        handler_file = LAMBDA_DIR / f"{lambda_name}.py"
        zf.write(handler_file, handler_file.name)
        
        # 3. Add shared services
        for file in SERVICES_DIR.glob("*.py"):
            zf.write(file, f"services/{file.name}")
            
        # 4. Add utils
        for file in UTILS_DIR.glob("*.py"):
            zf.write(file, f"utils/{file.name}")
            
        # 5. Add config and .env
        zf.write(BASE_DIR / "config.py", "config.py")
        if ENV_FILE.exists():
            zf.write(ENV_FILE, ".env")
            
    return zip_path

def deploy_to_aws(lambda_name, zip_path):
    """Uploads zip to S3 and updates Lambda function code."""
    bucket = get_s3_bucket()
    s3_key = f"deploy/{lambda_name}.zip"
    
    s3 = boto3.client('s3')
    lam = boto3.client('lambda')
    
    print(f"Uploading to s3://{bucket}/{s3_key}...")
    s3.upload_file(str(zip_path), bucket, s3_key)
    
    print(f"Updating Lambda function: {lambda_name}...")
    lam.update_function_code(
        FunctionName=lambda_name,
        S3Bucket=bucket,
        S3Key=s3_key
    )
    print(f"Successfully updated {lambda_name}")

def main():
    try:
        create_package()
        for name in LAMBDAS:
            zip_path = zip_lambda(name)
            try:
                deploy_to_aws(name, zip_path)
            except Exception as e:
                print(f"AWS Deployment failed for {name} (ZIP is still in {ZIP_OUTPUT_DIR.name}): {e}")
                
    finally:
        if PACKAGE_DIR.exists():
            shutil.rmtree(PACKAGE_DIR)
    
    print(f"\n--- Process Complete. Zips are available in: {ZIP_OUTPUT_DIR} ---")

if __name__ == "__main__":
    main()
