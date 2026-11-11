import os
import pytest
from fastapi.testclient import TestClient

# Mock environment variables before importing gateway
os.environ["DIFY_WEBHOOK_SECRET"] = "test_secret_123"
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "http://localhost:4317"

from gateway import app

client = TestClient(app)

def test_health_check():
    """Test health check route."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "arize_phoenix_endpoint" in data

def test_webhook_unauthorized():
    """Test webhook with invalid authorization header."""
    payload = {
        "event": "ping",
        "task_id": "test_task",
        "message_id": "test_msg",
        "conversation_id": "test_conv",
        "app_id": "test_app",
        "data": {}
    }
    response = client.post(
        "/webhook",
        json=payload,
        headers={"Authorization": "Bearer wrong_secret"}
    )
    assert response.status_code == 401
    assert "Invalid Dify Webhook secret token" in response.json()["detail"]

def test_webhook_ping_pong():
    """Test webhook validation ping challenge."""
    payload = {
        "event": "ping",
        "task_id": "test_task",
        "message_id": "test_msg",
        "conversation_id": "test_conv",
        "app_id": "test_app",
        "data": {}
    }
    response = client.post(
        "/webhook",
        json=payload,
        headers={"Authorization": "Bearer test_secret_123"}
    )
    assert response.status_code == 200
    assert response.json() == {"challenge": "pong"}

def test_webhook_message_end_processing():
    """Test processing of message_end events."""
    payload = {
        "event": "message_end",
        "task_id": "task_999",
        "message_id": "msg_888",
        "conversation_id": "conv_777",
        "app_id": "app_555",
        "data": {
            "inputs": {"question": "What is OpenTelemetry?"},
            "outputs": {"text": "An open observability framework."},
            "status": "completed",
            "metadata": {
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 20,
                    "total_tokens": 35
                },
                "total_price": 0.005
            }
        }
    }
    response = client.post(
        "/webhook",
        json=payload,
        headers={"Authorization": "Bearer test_secret_123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_event"] == "message_end"
    assert data["span_id"] == "msg_888"
    assert data["trace_id"] == "conv_777"
