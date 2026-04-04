from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.users import build_router


class UserServiceStub:
    def connect_wallet(self, db, wallet_address: str):
        _ = db
        return {"wallet_address": wallet_address, "status": "created"}

    def get_user(self, db, wallet_address: str):
        _ = db
        if wallet_address == "missing":
            return None
        return {"wallet_address": wallet_address, "status": "existing"}

    def get_all_users(self, db):
        _ = db
        return [{"wallet_address": "0x1"}, {"wallet_address": "0x2"}]


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
    assert response.json()["wallet_address"] == "0xabc"


def test_get_user_404_when_missing() -> None:
    client = _client()
    response = client.get("/v1/users/missing")
    assert response.status_code == 404


def test_list_users_ok() -> None:
    client = _client()
    response = client.get("/v1/users")
    assert response.status_code == 200
    assert len(response.json()) == 2
