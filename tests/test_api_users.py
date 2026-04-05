from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.users import build_router


class UserServiceStub:
    def connect_wallet(self, db, wallet_address: str):
        _ = db
        return {
            "wallet_address": wallet_address,
            "status": "created",
            "vault_id": 12,
            "pending_sync": False,
            "retry_after_seconds": 0,
            "sync_source": "onchain_scan",
        }

    def get_user(self, db, wallet_address: str):
        _ = db
        if wallet_address == "missing":
            return None
        return {
            "wallet_address": wallet_address,
            "vault_id": 12,
            "pending_sync": False,
            "retry_after_seconds": 0,
            "sync_source": "onchain_scan",
        }

    def get_user_vault_sync(self, db, wallet_address: str):
        _ = db
        if wallet_address == "missing":
            return None
        return {
            "wallet_address": wallet_address,
            "vault_id": 12,
            "pending_sync": False,
            "retry_after_seconds": 0,
            "sync_source": "onchain_scan",
        }

    def get_all_users(self, db):
        _ = db
        return [{"wallet_address": "0x1"}, {"wallet_address": "0x2"}]

    def get_user_investments(self, wallet_address: str):
        return {
            "wallet_address": wallet_address.lower(),
            "items": [
                {
                    "vault_id": 12,
                    "shares": "1000000000000000000",
                    "value": "1020000000000000000",
                    "profit": "20000000000000000",
                }
            ],
        }


def _get_db():
    yield object()


def _client():
    app = FastAPI()
    app.include_router(build_router(UserServiceStub(), _get_db))
    return TestClient(app)


def test_connect_wallet_ok() -> None:
    client = _client()
    response = client.post("/v1/users/connect", json={"wallet_address": "0xabc"})
    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == "0xabc"
    assert body["vault_id"] == 12
    assert body["pending_sync"] is False
    assert body["retry_after_seconds"] == 0


def test_get_user_404_when_missing() -> None:
    client = _client()
    response = client.get("/v1/users/missing")
    assert response.status_code == 404


def test_get_user_vault_sync_ok() -> None:
    client = _client()
    response = client.get("/v1/users/0xabc/vault-sync")
    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == "0xabc"
    assert body["vault_id"] == 12
    assert body["pending_sync"] is False


def test_get_user_vault_sync_404_when_missing() -> None:
    client = _client()
    response = client.get("/v1/users/missing/vault-sync")
    assert response.status_code == 404


def test_list_users_ok() -> None:
    client = _client()
    response = client.get("/v1/users")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_user_investments_ok() -> None:
    client = _client()
    response = client.get("/v1/users/0xAbC/investments")
    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == "0xabc"
    assert body["items"][0]["vault_id"] == 12
