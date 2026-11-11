import os
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# OpenTelemetry Tracing imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dify-telemetry-gateway")

app = FastAPI(
    title="Dify Telemetry Gateway for Arize Phoenix",
    description="Enterprise API Gateway to convert Dify Webhooks into OpenTelemetry spans sent to Arize Phoenix.",
    version="1.0.0"
)

# Load configuration
PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:4317")
PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT", "Dify-Telemetry-Gateway")
DIFY_WEBHOOK_SECRET = os.getenv("DIFY_WEBHOOK_SECRET", "dify_enterprise_secure_token_abc123")

# Initialize OpenTelemetry Tracer
resource = Resource(attributes={
    "service.name": "dify-orchestrator",
    "openinference.project.name": PHOENIX_PROJECT,
    "project.name": PHOENIX_PROJECT
})

provider = TracerProvider(resource=resource)
try:
    exporter = OTLPSpanExporter(endpoint=PHOENIX_COLLECTOR_ENDPOINT, insecure=True)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    logger.info(f"OpenTelemetry Tracer successfully initialized. Exporting to: {PHOENIX_COLLECTOR_ENDPOINT}")
except Exception as e:
    logger.warning(f"Failed to initialize OTLPSpanExporter ({e}). Falling back to local console span logging.")
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("dify.webhook.gateway")

# Pydantic Schemas for validation
class DifyWebhookPayload(BaseModel):
    event: str
    task_id: Optional[str] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    app_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "arize_phoenix_endpoint": PHOENIX_COLLECTOR_ENDPOINT,
        "project": PHOENIX_PROJECT
    }

@app.post("/webhook", tags=["Telemetry"])
async def receive_dify_webhook(
    request: Request,
    payload: DifyWebhookPayload,
    authorization: Optional[str] = Header(None)
):
    """
    Receives events from Dify Webhooks, extracts workflow/model telemetry metrics,
    creates custom OpenTelemetry Spans matching Arize Phoenix / OpenInference standards,
    and forwards them to Phoenix OTel Collector.
    """
    # 1. Validate authorization secret if configured
    if DIFY_WEBHOOK_SECRET:
        expected_auth = f"Bearer {DIFY_WEBHOOK_SECRET}"
        if not authorization or authorization != expected_auth:
            logger.warning("Unauthorized webhook request received.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Dify Webhook secret token"
            )

    event_type = payload.event
    logger.info(f"Processing webhook event: {event_type} (MsgID: {payload.message_id}, ConvID: {payload.conversation_id})")

    # Handle webhook validation ping
    if event_type == "ping":
        return JSONResponse(content={"challenge": "pong"}, status_code=200)

    # 2. Extract telemetry and model invocation data
    data = payload.data or {}
    inputs = data.get("inputs", {})
    outputs = data.get("outputs", {})
    status_str = data.get("status", "completed")
    error_msg = data.get("error", None)

    # Core identification tokens
    span_name = f"dify.{event_type}"
    trace_id = payload.conversation_id or "default-trace-id"
    span_id = payload.message_id or payload.task_id or "default-span-id"

    # Start and execute custom OTel Span mapping OpenInference semantic attributes
    with tracer.start_as_current_span(span_name) as span:
        # Set OpenInference and Arize Phoenix standard attributes
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("dify.event_type", event_type)
        span.set_attribute("dify.app_id", payload.app_id or "unknown")
        span.set_attribute("dify.conversation_id", payload.conversation_id or "unknown")
        span.set_attribute("dify.message_id", payload.message_id or "unknown")

        if payload.task_id:
            span.set_attribute("dify.task_id", payload.task_id)

        # Mapping Inputs & Outputs
        if inputs:
            span.set_attribute("input.value", json.dumps(inputs))
            span.set_attribute("input.mime_type", "application/json")
        elif "query" in data:
            span.set_attribute("input.value", data.get("query"))
            span.set_attribute("input.mime_type", "text/plain")

        if outputs:
            span.set_attribute("output.value", json.dumps(outputs))
            span.set_attribute("output.mime_type", "application/json")
        elif "answer" in data:
            span.set_attribute("output.value", data.get("answer"))
            span.set_attribute("output.mime_type", "text/plain")

        # Map execution performance & LLM execution metadata if available in message_end
        if event_type in ["message_end", "workflow_finished"]:
            metadata = data.get("metadata", {})
            usage = metadata.get("usage", {})

            # Map Token Usage
            if usage:
                span.set_attribute("llm.usage.prompt_tokens", usage.get("prompt_tokens", 0))
                span.set_attribute("llm.usage.completion_tokens", usage.get("completion_tokens", 0))
                span.set_attribute("llm.usage.total_tokens", usage.get("total_tokens", 0))

            # Map Latency & Speeds
            total_price = metadata.get("total_price", 0.0)
            if total_price:
                span.set_attribute("llm.cost", float(total_price))

        # Handle errors and status tracing
        if error_msg or status_str == "failed":
            span.set_status(Status(StatusCode.ERROR, error_msg or "Execution failed"))
            span.set_attribute("error.message", error_msg or "Unknown error occurred")
        else:
            span.set_status(Status(StatusCode.OK))

    return {
        "status": "success",
        "processed_event": event_type,
        "span_id": span_id,
        "trace_id": trace_id
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    logger.info(f"Starting Dify Webhook Telemetry Gateway on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
