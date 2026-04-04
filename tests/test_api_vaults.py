from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.vaults import build_router


class VaultServiceStub:
    def __init__(self):
        self.calls = []

    def import_vault(self, vault_address: str, chain_id: int):
        self.calls.append(("import_vault", vault_address, chain_id))
        return {"managerAddress": vault_address, "chainId": chain_id}

    def get_all_balances(self):
        return {"USDC": {"balance": 123, "decimals": 6, "symbol": "USDC"}}

    def get_token_balance(self, token_address: str):
        self.calls.append(("get_token_balance", token_address))
        return 42

    def get_token_decimals(self, token_address: str):
        self.calls.append(("get_token_decimals", token_address))
        return 6

    def get_token_symbol(self, token_address: str):
        self.calls.append(("get_token_symbol", token_address))
        return "USDC"

    def build_create_vault_tx(self, owner_fee_bps: int):
        self.calls.append(("build_create_vault_tx", owner_fee_bps))
        return {"ownerFeeBps": owner_fee_bps}

    def build_deposit_tx(self, vault_id: int, amount: int, receiver: str):
        self.calls.append(("build_deposit_tx", vault_id, amount, receiver))
        return {"vaultId": vault_id, "amount": str(amount), "receiver": receiver}

    def build_withdraw_tx(self, vault_id: int, shares: int, receiver: str):
        self.calls.append(("build_withdraw_tx", vault_id, shares, receiver))
        return {"vaultId": vault_id, "shares": str(shares), "receiver": receiver}

    def build_agent_swap_tx(self, vault_id: int, target: str, data: str, min_asset_delta: int, value: int):
        self.calls.append(("build_agent_swap_tx", vault_id, target, data, min_asset_delta, value))
        return {"vaultId": vault_id, "target": target, "data": data}

    def execute_agent_swap(self, vault_id: int, target: str, data: str, min_asset_delta: int, value: int):
        self.calls.append(("execute_agent_swap", vault_id, target, data, min_asset_delta, value))
        return {"txHash": "0xabc", "vaultId": vault_id}

    def get_user_position(self, vault_id: int, user_address: str):
        self.calls.append(("get_user_position", vault_id, user_address))
        return {"vaultId": str(vault_id), "user": user_address, "shares": "0"}


def _client():
    app = FastAPI()
    stub = VaultServiceStub()
    app.include_router(build_router(stub))
    return TestClient(app), stub


def test_build_deposit_endpoint() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/vaults/deposit/build",
        json={"vault_id": 1, "amount": "1000", "receiver": "0xabc"},
    )

    assert response.status_code == 200
    assert response.json()["vaultId"] == 1
    assert ("build_deposit_tx", 1, 1000, "0xabc") in stub.calls


def test_build_withdraw_endpoint() -> None:
    client, stub = _client()

    response = client.post(
        "/v1/vaults/withdraw/build",
        json={"vault_id": 1, "shares": "500", "receiver": "0xabc"},
    )

    assert response.status_code == 200
    assert response.json()["shares"] == "500"
    assert ("build_withdraw_tx", 1, 500, "0xabc") in stub.calls


def test_token_balance_endpoint() -> None:
    client, _ = _client()

    response = client.get("/v1/vaults/balance/0xToken")

    assert response.status_code == 200
    body = response.json()
    assert body["balance_raw"] == 42
    assert body["decimals"] == 6
    assert body["symbol"] == "USDC"
