# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install curl for the health check (slim image does not include it by default)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code into the container
COPY . .

# Expose the API port
EXPOSE 8000

# Health check — verifies the FastAPI /health endpoint is responding.
# Failure after 3 retries causes ECS to replace the task automatically.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run with 2 workers for lightweight parallelism on Fargate.
# --workers 2 is appropriate for 512 CPU units (0.5 vCPU).
# Do NOT use nohup — that is an EC2-era anti-pattern; Fargate manages the process lifecycle.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
