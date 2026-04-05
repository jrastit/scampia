from types import SimpleNamespace

from app.services.user_service import UserService


class MutableVaultServiceStub:
    def __init__(self):
        self.items = []

    def list_vaults(self):
        return {"items": self.items}


def test_vault_id_appears_in_user_profile_after_vault_creation(monkeypatch) -> None:
    wallet = "0xabc123"
    user = SimpleNamespace(
        wallet_address=wallet,
        safe_address="0xmanager",
        vault_address="0xmanager",
        network="ethereum-sepolia",
        chain_id=11155111,
        created_at="2026-04-05T12:00:00Z",
        is_active=True,
    )

    state = {"created": False}

    def fake_get_user_by_wallet(_db, _wallet):
        if state["created"]:
            return user
        return None

    def fake_create_user(db, wallet_address, vault_address, network, chain_id):
        _ = db
        state["created"] = True
        user.wallet_address = wallet_address.lower()
        user.vault_address = vault_address.lower()
        user.safe_address = vault_address.lower()
        user.network = network
        user.chain_id = chain_id
        return user

    monkeypatch.setattr("app.services.user_service.user_data.get_user_by_wallet", fake_get_user_by_wallet)
    monkeypatch.setattr("app.services.user_service.user_data.create_user", fake_create_user)
    monkeypatch.setattr("app.services.user_service.settings.vault_manager_address", "0xmanager")
    monkeypatch.setattr("app.services.user_service.settings.vault_address", "0xmanager")
    monkeypatch.setattr("app.services.user_service.settings.network", "ethereum-sepolia")
    monkeypatch.setattr("app.services.user_service.settings.chain_id", 11155111)

    vault_service = MutableVaultServiceStub()
    service = UserService(vault_service)

    # Step 1: user connects before on-chain scan sees the new vault.
    connect_response = service.connect_wallet(object(), wallet)
    assert connect_response["status"] == "created"
    assert connect_response["vault_id"] is None
    assert connect_response["pending_sync"] is True
    assert connect_response["retry_after_seconds"] == 2

    # Step 2: after vault creation is visible on-chain, profile polling gets vault_id.
    vault_service.items = [
        {"vault_id": 42, "owner": wallet.upper()},
    ]
    profile_response = service.get_user(object(), wallet)
    assert profile_response is not None
    assert profile_response["vault_id"] == 42
    assert profile_response["pending_sync"] is False
    assert profile_response["retry_after_seconds"] == 0

    # Step 3: a later connect call should also return the resolved vault_id.
    connect_existing_response = service.connect_wallet(object(), wallet)
    assert connect_existing_response["status"] == "existing"
    assert connect_existing_response["vault_id"] == 42
    assert connect_existing_response["pending_sync"] is False


def test_vault_id_falls_back_to_global_latest_when_owner_differs(monkeypatch) -> None:
    wallet = "0xb724531ad056340bbf611ac2e68502b26d394179"
    user = SimpleNamespace(
        wallet_address=wallet,
        safe_address="0xmanager",
        vault_address="0xmanager",
        network="ethereum-sepolia",
        chain_id=11155111,
        created_at="2026-04-05T12:00:00Z",
        is_active=True,
    )

    def fake_get_user_by_wallet(_db, _wallet):
        return user

    monkeypatch.setattr("app.services.user_service.user_data.get_user_by_wallet", fake_get_user_by_wallet)

    vault_service = MutableVaultServiceStub()
    vault_service.items = [
        {"vault_id": 100, "owner": "0x1111111111111111111111111111111111111111"},
        {"vault_id": 101, "owner": "0x2222222222222222222222222222222222222222"},
    ]
    service = UserService(vault_service)

    profile_response = service.get_user(object(), wallet)
    assert profile_response is not None
    assert profile_response["wallet_address"] == wallet
    assert profile_response["vault_id"] == 101
    assert profile_response["pending_sync"] is False
    assert profile_response["retry_after_seconds"] == 0
    assert profile_response["sync_source"] == "global_latest"
