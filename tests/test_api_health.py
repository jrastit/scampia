from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import build_router


def test_health_endpoint_returns_expected_payload() -> None:
    settings = SimpleNamespace(
        app_name="scampia",
        network="ethereum-sepolia",
        chain_id=11155111,
        safe_tx_service_base="https://safe-transaction-sepolia.safe.global",
    )
    app = FastAPI()
    app.include_router(build_router(settings))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "app": "scampia",
        "network": "ethereum-sepolia",
        "chainId": 11155111,
        "safeTxServiceBase": "https://safe-transaction-sepolia.safe.global",
    }
