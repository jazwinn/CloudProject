from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, graph, clusters, image

from contextlib import asynccontextmanager
from services.database import Base, get_engine

from fastapi import Request
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (idempotent, only runs if they don't exist)
    # This ensures the DB is set up correctly without needing local access.
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        print("Database tables verified.")
    except Exception as e:
        print(f"Database verification failed (check connection settings): {e}")
    yield

app = FastAPI(
    title="CloudGraph API",
    description="Backend for CloudGraph photo management platform", 
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your Amplify frontend, Change as Needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(clusters.router, prefix="/api")
app.include_router(image.router, prefix="/api")

@app.get("/health")
def health_check():
    """Health check endpoint to ensure API is running."""
    return {"status": "ok"}


@app.options("/{full_path:path}")
async def preflight_handler(full_path: str, request: Request):
    return JSONResponse(
        status_code=200,
        content={},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Credentials": "true"
        }
    )


  