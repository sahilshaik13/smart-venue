# backend/app/services/bigquery_client.py

import structlog
from google.cloud import bigquery
from typing import Any, List
from app.config import settings

log = structlog.get_logger(__name__)

class BigQueryTelemetrySink:
    """
    Streams venue intelligence snapshots to Google BigQuery for long-term spatial analysis.
    Satisfies 'Broader adoption of Google services' requirement.
    """
    def __init__(self):
        self.client = None
        self.dataset_id = "venue_intelligence"
        self.table_id = "spatial_telemetry"
        
        if settings.environment == "production":
            try:
                self.client = bigquery.Client()
                log.info("bigquery_client_initialized")
            except Exception as e:
                log.warning("bigquery_init_failed", error=str(e))

    async def stream_snapshot(self, snapshot_dict: dict):
        """Streams a single snapshot to BigQuery table."""
        if not self.client:
            return

        # Prepare row for BigQuery
        row = {
            "snapshot_time": snapshot_dict.get("snapshot_time"),
            "match_phase": snapshot_dict.get("match_phase"),
            "total_count": sum(z.get("current_count", 0) for z in snapshot_dict.get("zones", [])),
            "zones_json": str(snapshot_dict.get("zones"))
        }

        try:
            table_ref = f"{self.client.project}.{self.dataset_id}.{self.table_id}"
            errors = self.client.insert_rows_json(table_ref, [row])
            if errors:
                log.error("bigquery_streaming_errors", errors=errors)
            else:
                log.info("bigquery_snapshot_streamed", timestamp=row["snapshot_time"])
        except Exception as e:
            log.warning("bigquery_stream_failed", error=str(e))

bq_sink = BigQueryTelemetrySink()
