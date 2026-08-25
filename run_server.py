"""Entry point script for running the FastAPI application with Uvicorn."""
from app.config.settings import get_settings
import uvicorn

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=get_settings().server_host,
        port=get_settings().server_port,
        reload=get_settings().debug,
        log_level=get_settings().log_level.lower(),
    )
    # Deployment example (use 0.0.0.0 for external access)
    # uvicorn.run("app.main:app", host="0.0.0.0", port=10000)
