import sys
import types

if "eth_account" not in sys.modules:
    eth_account_stub = types.ModuleType("eth_account")

    class _Account:
        @staticmethod
        def from_key(_key):
            return None

    eth_account_stub.Account = _Account
    sys.modules["eth_account"] = eth_account_stub

if "web3" not in sys.modules:
    web3_stub = types.ModuleType("web3")

    class _Web3:
        class HTTPProvider:
            def __init__(self, _url: str):
                pass

        def __init__(self, _provider):
            self.eth = types.SimpleNamespace(contract=lambda **_kwargs: None)

        @staticmethod
        def to_checksum_address(value: str) -> str:
            return value

    web3_stub.Web3 = _Web3
    sys.modules["web3"] = web3_stub

from app.services.vault_service import VaultService


class _Call:
    def __init__(self, value):
        self._value = value

    def call(self):
        return self._value


class _Functions:
    def __init__(self, asset_value: str):
        self._asset_value = asset_value

    def asset(self):
        return _Call(self._asset_value)


class _VaultContract:
    def __init__(self, asset_value: str, calldata: str = "0xdeadbeef"):
        self.functions = _Functions(asset_value)
        self._calldata = calldata

    def encode_abi(self, method: str, args):
        _ = (method, args)
        return self._calldata


class _Eth:
    def __init__(self, balance: int):
        self._balance = balance

    def get_balance(self, _address: str) -> int:
        return self._balance


class _W3:
    def __init__(self, balance: int):
        self.eth = _Eth(balance)


def _service_with_basics() -> VaultService:
    service = VaultService()
    service.manager_contract_address = lambda: "0x1111111111111111111111111111111111111111"
    service._checksum = lambda value: value
    return service


def test_build_deposit_tx_sets_value_for_native_asset() -> None:
    service = _service_with_basics()
    service.is_native_asset_mode = lambda: True
    service._vault_contract = lambda: _VaultContract("0x0000000000000000000000000000000000000000")

    tx = service.build_deposit_tx(vault_id=7, amount=12345, receiver="0x2222222222222222222222222222222222222222")

    assert tx["vaultId"] == 7
    assert tx["amount"] == "12345"
    assert tx["value"] == "12345"
    assert tx["isNativeAsset"] is True


def test_build_deposit_tx_keeps_zero_value_for_erc20_asset() -> None:
    service = _service_with_basics()
    service.is_native_asset_mode = lambda: False
    service._vault_contract = lambda: _VaultContract("0x3333333333333333333333333333333333333333")

    tx = service.build_deposit_tx(vault_id=9, amount=456, receiver="0x2222222222222222222222222222222222222222")

    assert tx["vaultId"] == 9
    assert tx["amount"] == "456"
    assert tx["value"] == "0"
    assert tx["isNativeAsset"] is False


def test_get_deposit_precheck_native_reports_balance_as_sufficient_allowance() -> None:
    service = _service_with_basics()
    service.w3 = _W3(balance=2_000)
    service.is_native_asset_mode = lambda: True
    service._vault_contract = lambda: _VaultContract("0x0000000000000000000000000000000000000000")

    precheck = service.get_deposit_precheck(
        vault_id=3,
        owner_address="0x4444444444444444444444444444444444444444",
        amount=1_500,
    )

    assert precheck["isNativeAsset"] is True
    assert precheck["assetSymbol"] == "ETH"
    assert precheck["value"] == "1500"
    assert precheck["requiresApproval"] is False
    assert precheck["allowance"] == "2000"
    assert precheck["allowanceSufficient"] is True
