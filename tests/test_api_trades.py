from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.trades import build_router
from app.services.policy_service import PolicyViolation


class TradeServiceStub:
    def __init__(self):
        self.calls = []

    def quote_trade(self, **kwargs):
        self.calls.append(("quote_trade", kwargs))
        return {"ok": True, "kind": "quote"}

    def build_trade(self, **kwargs):
        self.calls.append(("build_trade", kwargs))
        if kwargs.get("token_in") == "forbidden":
            raise PolicyViolation("token_in is not allowed")
        return {"ok": True, "kind": "build"}

    def prepare_vault_trade(self, **kwargs):
        self.calls.append(("prepare_vault_trade", kwargs))
        return {"ok": True, "kind": "prepare"}

    def execute_vault_swap(self, **kwargs):
        self.calls.append(("execute_vault_swap", kwargs))
        return {"ok": True, "kind": "execute"}


def _client():
    settings = SimpleNamespace(
        trade_allowed_tokens_in=["0xIn"],
        trade_allowed_tokens_out=["0xOut"],
        trade_max_input_per_tx=1_000_000,
    )
    app = FastAPI()
    stub = TradeServiceStub()
    app.include_router(build_router(stub, settings))
    return TestClient(app), stub


def test_quote_endpoint_uses_wallet_address() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/trades/quote",
        json={
            "chain_id": 11155111,
            "vault_address": "0xManager",
            "token_in": "0xIn",
            "token_out": "0xOut",
            "amount_in": "1000",
            "slippage_bps": 50,
        },
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "quote"
    method, kwargs = stub.calls[-1]
    assert method == "quote_trade"
    assert kwargs["wallet_address"] == "0xManager"


def test_prepare_vault_tx_requires_vault_id() -> None:
    client, _ = _client()

    response = client.post(
        "/v1/trades/prepare-vault-tx",
        json={
            "chain_id": 11155111,
            "vault_address": "0xManager",
            "token_in": "0xIn",
            "token_out": "0xOut",
            "amount_in": "1000",
            "slippage_bps": 50,
        },
    )

    assert response.status_code == 400
    assert "vault_id is required" in response.json()["detail"]


def test_build_trade_policy_violation_maps_to_403() -> None:
    client, _ = _client()

    response = client.post(
        "/v1/trades/build",
        json={
            "chain_id": 11155111,
            "vault_address": "0xManager",
            "token_in": "forbidden",
            "token_out": "0xOut",
            "amount_in": "1000",
            "slippage_bps": 50,
        },
    )

    assert response.status_code == 403
    assert "not allowed" in response.json()["detail"]
