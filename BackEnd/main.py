from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload

app = FastAPI(
    title="CloudGraph API",
    description="Backend for CloudGraph photo management platform",
    version="1.0.0"
)

# Allow CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")

@app.get("/health")
def health_check():
    """Health check endpoint to ensure API is running."""
    return {"status": "ok"}
