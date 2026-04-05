from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ens import build_router


class ENSServiceStub:
    def __init__(self):
        self.calls = []
        self.w3 = SimpleNamespace(
            to_hex=lambda value: value if isinstance(value, str) else "0x" + bytes(value).hex()
        )

    def build_set_config_tx(self, registry_address=None, resolver_address=None, parent_name=None):
        self.calls.append(("build_set_config_tx", registry_address, resolver_address, parent_name))
        return {"to": "0xvault", "data": "0xabc"}

    def set_config(self, registry_address=None, resolver_address=None, parent_name=None):
        self.calls.append(("set_config", registry_address, resolver_address, parent_name))
        return {"tx_hash": "0x1"}

    def build_register_vault_tx(self, vault_id: int, label: str):
        self.calls.append(("build_register_vault_tx", vault_id, label))
        return {"vaultId": str(vault_id), "label": label}

    def register_vault(self, vault_id: int, label: str, texts=None):
        self.calls.append(("register_vault", vault_id, label, texts))
        return {"vaultId": str(vault_id), "label": label, "tx_hashes": ["0x2"]}

    def build_set_vault_texts_tx(self, vault_id: int, texts):
        self.calls.append(("build_set_vault_texts_tx", vault_id, texts))
        return {"vaultId": str(vault_id), "texts": texts}

    def set_vault_text_records(self, vault_id: int, texts):
        self.calls.append(("set_vault_text_records", vault_id, texts))
        return {"vaultId": str(vault_id), "texts": texts}

    def get_vault_profile(self, vault_id: int, text_keys=None):
        self.calls.append(("get_vault_profile", vault_id, text_keys))
        return {"vaultId": str(vault_id), "configured": True, "name": "vault.scampia.eth"}

    def get_profile(self, name: str, text_keys=None):
        self.calls.append(("get_profile", name, text_keys))
        return {"name": name, "address": "0xabc"}


def _settings():
    return SimpleNamespace(
        network="ethereum-sepolia",
        chain_id=11155111,
        vault_manager_address="0x0000000000000000000000000000000000000001",
        vault_address="0x0000000000000000000000000000000000000001",
        ens_parent_name="scampia.eth",
        ens_registry_address="0x0000000000000000000000000000000000000002",
        ens_public_resolver_address="0x0000000000000000000000000000000000000003",
    )


def _client():
    app = FastAPI()
    stub = ENSServiceStub()
    app.include_router(build_router(stub, None, _settings()))
    return TestClient(app), stub


def test_get_ens_config_ok() -> None:
    client, _ = _client()

    response = client.get("/v1/ens/config")

    assert response.status_code == 200
    body = response.json()
    assert body["network"] == "ethereum-sepolia"
    assert body["chainId"] == 11155111


def test_build_register_vault_ens_ok() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/ens/vaults/register/build",
        json={"vault_id": 12, "label": "vault-12"},
    )

    assert response.status_code == 200
    assert response.json()["vaultId"] == "12"
    assert ("build_register_vault_tx", 12, "vault-12") in stub.calls


def test_set_vault_policy_ok() -> None:
    client, stub = _client()

    response = client.put(
        "/v1/ens/vaults/12/policy",
        json={"stop_loss_pct": 5.0, "max_open_positions": 3},
    )

    assert response.status_code == 200
    calls = [c for c in stub.calls if c[0] == "set_vault_text_records"]
    assert len(calls) == 1
    _, vault_id, texts = calls[0]
    assert vault_id == 12
    assert texts["stop_loss_pct"] == "5"
    assert texts["max_open_positions"] == "3"


def test_build_ens_config_tx_ok() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/ens/config/build",
        json={"parent_name": "scampia.eth"},
    )

    assert response.status_code == 200
    assert response.json()["to"] == "0xvault"
    assert any(c[0] == "build_set_config_tx" for c in stub.calls)


def test_sync_ens_config_ok() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/ens/config/sync",
        json={"parent_name": "scampia.eth"},
    )

    assert response.status_code == 200
    assert response.json()["tx_hash"] == "0x1"
    assert any(c[0] == "set_config" for c in stub.calls)


def test_build_vault_policy_tx_ok() -> None:
    client, stub = _client()

    response = client.put(
        "/v1/ens/vaults/policy/build",
        json={"vault_id": 12, "take_profit_pct": 9.5},
    )

    assert response.status_code == 200
    calls = [c for c in stub.calls if c[0] == "build_set_vault_texts_tx"]
    assert len(calls) == 1
    _, vault_id, texts = calls[0]
    assert vault_id == 12
    assert texts["take_profit_pct"] == "9.5"


def test_get_vault_ens_profile_ok() -> None:
    client, stub = _client()

    response = client.get("/v1/ens/vaults/12")

    assert response.status_code == 200
    assert response.json()["vaultId"] == "12"
    assert any(c[0] == "get_vault_profile" and c[1] == 12 for c in stub.calls)


def test_get_name_profile_ok() -> None:
    client, stub = _client()

    response = client.get("/v1/ens/names/vault.scampia.eth")

    assert response.status_code == 200
    assert response.json()["name"] == "vault.scampia.eth"
    assert any(c[0] == "get_profile" and c[1] == "vault.scampia.eth" for c in stub.calls)
