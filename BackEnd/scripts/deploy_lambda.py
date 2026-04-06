import os
import shutil
import subprocess
import zipfile
import boto3
from pathlib import Path

# Configuration
LAMBDAS = ["image_processor"]
BASE_DIR = Path(__file__).parent.parent
LAMBDA_DIR = BASE_DIR / "lambda"
SERVICES_DIR = BASE_DIR / "services"
UTILS_DIR = BASE_DIR / "utils"
PACKAGE_DIR = BASE_DIR / "package"
ZIP_OUTPUT_DIR = BASE_DIR / "deploy_zips"
ENV_FILE = BASE_DIR / ".env"

# Per-lambda requirements — only what each Lambda actually needs
LAMBDA_REQUIREMENTS = {
    "image_processor": [
        "boto3>=1.28.0",
        "piexif>=1.1.3",
        "pydantic>=2.0.0",
        "Pillow>=10.0.0",
        "pillow-heif>=0.13.0",
        "pydantic-settings>=2.0.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
    ],
}

# Directories to delete entirely from packages
STRIP_DIRS = {
    "__pycache__",
    "tests", "test",
    "examples", "example",
    "benchmarks",
    "bin",
}

# File extensions to delete
STRIP_EXTENSIONS = {
    ".pyc", ".pyo",
    ".pyd",               # Windows DLLs
    ".exe",               # Windows executables
    ".md", ".rst",
    ".h", ".c", ".cpp",
    ".typed",
}

# Specific filenames to always delete
STRIP_FILES = {
    "METADATA", "RECORD", "WHEEL", "INSTALLER", "REQUESTED",
    "LICENSE", "LICENSE.txt", "COPYING", "NOTICE",
    "README", "README.md", "README.rst",
    "setup.py", "setup.cfg",
}

def load_env():
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ[key] = val

def get_s3_bucket():
    if not ENV_FILE.exists():
        return "cloudgraph-bucket"
    with open(ENV_FILE, "r") as f:
        for line in f:
            if line.startswith("S3_BUCKET_NAME="):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "cloudgraph-bucket"


def strip_package_dir(package_dir: Path):
    """Aggressively remove unnecessary files to shrink zip size."""
    print("  Stripping unnecessary files...")
    removed_bytes = 0

    for root, dirs, files in os.walk(package_dir, topdown=True):
        root_path = Path(root)

        dirs_to_remove = []
        for d in dirs:
            dir_path = root_path / d
            should_remove = (
                d in STRIP_DIRS or
                d.endswith(".dist-info") or
                d.endswith(".egg-info") or
                d == "__pycache__"
            )
            if should_remove:
                size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                removed_bytes += size
                shutil.rmtree(dir_path, ignore_errors=True)
                dirs_to_remove.append(d)

        for d in dirs_to_remove:
            dirs.remove(d)

        for file in files:
            file_path = root_path / file
            should_remove = (
                file_path.suffix in STRIP_EXTENSIONS or
                file in STRIP_FILES or
                file.startswith("LICENSE") or
                file.startswith("COPYING") or
                file.startswith("README")
            )
            if should_remove:
                removed_bytes += file_path.stat().st_size
                file_path.unlink()

    print(f"  Stripped {removed_bytes / 1024 / 1024:.1f} MB of unnecessary files")


def create_package(lambda_name: str, requirements: list) -> Path:
    package_dir = BASE_DIR / f"package_{lambda_name}"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()

    temp_download_dir = BASE_DIR / f"temp_downloads_{lambda_name}"
    if temp_download_dir.exists():
        shutil.rmtree(temp_download_dir)
    temp_download_dir.mkdir()

    temp_req = BASE_DIR / f"temp_req_{lambda_name}.txt"
    temp_req.write_text("\n".join(requirements))

    try:
        print(f"  Downloading dependencies for {lambda_name}...")
        subprocess.check_call([
            "python", "-m", "pip", "download",
            "-r", str(temp_req),
            "-d", str(temp_download_dir),
            "--platform", "manylinux2014_x86_64",
            "--only-binary=:all:",
            "--python-version", "3.12",
            "--implementation", "cp",
        ])

        print(f"  Extracting wheels...")
        for whl in temp_download_dir.glob("*.whl"):
            with zipfile.ZipFile(whl, 'r') as z:
                z.extractall(package_dir)

        strip_package_dir(package_dir)

    finally:
        if temp_download_dir.exists():
            shutil.rmtree(temp_download_dir)
        temp_req.unlink(missing_ok=True)

    return package_dir


def get_dir_size(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / 1024 / 1024


def zip_lambda(lambda_name: str, package_dir: Path) -> Path:
    zip_path = ZIP_OUTPUT_DIR / f"{lambda_name}.zip"
    print(f"  Zipping {lambda_name}...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # 1. Add dependencies
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(package_dir)
                zf.write(full_path, rel_path)

        # 2. Add Lambda handler
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

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"  Final zip size: {size_mb:.1f} MB")
    if size_mb > 50:
        print(f"  WARNING: {lambda_name}.zip is {size_mb:.1f} MB — exceeds 50MB limit!")
    return zip_path


def deploy_to_aws(lambda_name: str, zip_path: Path):
    bucket = get_s3_bucket()
    s3_key = f"deploy/{lambda_name}.zip"

    s3 = boto3.client('s3')
    lam = boto3.client('lambda')

    print(f"  Uploading to s3://{bucket}/{s3_key}...")
    s3.upload_file(str(zip_path), bucket, s3_key)

    print(f"  Updating Lambda function...")
    lam.update_function_code(
        FunctionName=lambda_name,
        S3Bucket=bucket,
        S3Key=s3_key
    )
    print(f"  Done.")


def main():
    load_env()
    if not ZIP_OUTPUT_DIR.exists():
        ZIP_OUTPUT_DIR.mkdir()

    for name in LAMBDAS:
        print(f"\n=== {name} ===")
        package_dir = None
        try:
            package_dir = create_package(name, LAMBDA_REQUIREMENTS[name])
            print(f"  Package size before zip: {get_dir_size(package_dir):.1f} MB")
            zip_path = zip_lambda(name, package_dir)
            try:
                deploy_to_aws(name, zip_path)
            except Exception as e:
                print(f"  AWS deployment failed (zip saved to {ZIP_OUTPUT_DIR.name}): {e}")
        finally:
            if package_dir and package_dir.exists():
                shutil.rmtree(package_dir)

    print(f"\n=== Complete. Zips in: {ZIP_OUTPUT_DIR} ===")


if __name__ == "__main__":
    main()