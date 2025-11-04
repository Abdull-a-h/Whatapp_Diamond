from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
import time
from app.config import get_settings
from app.routes import users, uploads, diamonds, designs, messages
from app.utils.logger import get_logger, log_to_database
from app.utils.exceptions import BaseAPIException
import app.services.whatsapp_client as whatsapp_client
from app.services.whatsapp_client import verify_webhook, handle_webhook

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="WhatsApp Diamond Bot API",
    description="AI-powered WhatsApp chatbot for diamond/jewelry design automation",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================
# WhatsApp Webhook Endpoints
# ==============================================================
@app.get("/webhook")
async def webhook_verify(request: Request):
    return await verify_webhook(request)

@app.post("/webhook")
async def webhook_receive(request: Request):
    return await handle_webhook(request)

# ==============================================================
# Middleware
# ==============================================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ==============================================================
# Exception Handlers
# ==============================================================
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "detail": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    await log_to_database("api", "error", f"Unexpected error: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.app_env == "development" else None
        }
    )

# ==============================================================
# Routers
# ==============================================================
app.include_router(users.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(diamonds.router, prefix="/api/v1")
app.include_router(designs.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")

# ==============================================================
# Health Check Endpoints
# ==============================================================
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "success": True,
        "message": "WhatsApp Diamond Bot API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "success": True,
        "status": "healthy",
        "environment": settings.app_env
    }

@app.get("/api/v1/health")
async def api_health_check():
    """API + Database health check."""
    try:
        from app.database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        supabase.table("users").select("id").limit(1).execute()

        return {
            "success": True,
            "status": "healthy",
            "database": "connected",
            "environment": settings.app_env
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

# ==============================================================
# Startup / Shutdown Events
# ==============================================================
@app.on_event("startup")
async def startup_event():
    """Run on app startup."""
    logger.info(f"Starting WhatsApp Diamond Bot API v2.0.0 - Environment: {settings.app_env}")
    await log_to_database("system", "info", "Application started")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown."""
    logger.info("Shutting down WhatsApp Diamond Bot API")
    await log_to_database("system", "info", "Application shutdown")

# ==============================================================
# Entry Point
# ==============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development"
    )