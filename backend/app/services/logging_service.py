# backend/app/services/logging_service.py

import os
import structlog
import logging
from google.cloud import logging as gcp_logging
from app.config import settings

def setup_cloud_logging():
    """
    Integrates the application with Google Cloud Logging.
    Uses structured JSON logs for better production observability.
    """
    if settings.environment == "production":
        # 1. Initialize GCP Logging Client
        client = gcp_logging.Client()
        client.setup_logging()
        
        # 2. Configure structlog to play nice with GCP log severity
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer()
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        return True
    return False

# Initialize logging on import
cloud_logging_enabled = setup_cloud_logging()
log = structlog.get_logger(__name__)
if cloud_logging_enabled:
    log.info("gcp_cloud_logging_activated", resource_type="cloud_run_revision")
else:
    log.info("local_logging_active", env=settings.environment)
