import pytest

from app.services.policy_service import PolicyService, PolicyViolation


@pytest.mark.parametrize(
    "token",
    [
        "eth",
        "native",
        "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "0x0000000000000000000000000000000000000000",
    ],
)
def test_validate_trade_rejects_native_token_in(token: str) -> None:
    service = PolicyService()

    with pytest.raises(PolicyViolation, match="native token is not supported as token_in"):
        service.validate_trade(
            vault_address="0x1111111111111111111111111111111111111111",
            recipient="0x1111111111111111111111111111111111111111",
            token_in=token,
            token_out="0x2222222222222222222222222222222222222222",
            amount_in=1,
            allowed_tokens_in=[],
            allowed_tokens_out=[],
            max_input_per_tx=0,
        )


@pytest.mark.parametrize(
    "token",
    [
        "eth",
        "native",
        "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "0x0000000000000000000000000000000000000000",
    ],
)
def test_validate_trade_rejects_native_token_out(token: str) -> None:
    service = PolicyService()

    with pytest.raises(PolicyViolation, match="native token is not supported as token_out"):
        service.validate_trade(
            vault_address="0x1111111111111111111111111111111111111111",
            recipient="0x1111111111111111111111111111111111111111",
            token_in="0x2222222222222222222222222222222222222222",
            token_out=token,
            amount_in=1,
            allowed_tokens_in=[],
            allowed_tokens_out=[],
            max_input_per_tx=0,
        )


def test_validate_trade_accepts_erc20_addresses() -> None:
    service = PolicyService()

    service.validate_trade(
        vault_address="0x1111111111111111111111111111111111111111",
        recipient="0x1111111111111111111111111111111111111111",
        token_in="0x2222222222222222222222222222222222222222",
        token_out="0x3333333333333333333333333333333333333333",
        amount_in=1,
        allowed_tokens_in=[],
        allowed_tokens_out=[],
        max_input_per_tx=0,
    )


def test_validate_trade_allows_native_when_enabled() -> None:
    service = PolicyService()

    service.validate_trade(
        vault_address="0x1111111111111111111111111111111111111111",
        recipient="0x1111111111111111111111111111111111111111",
        token_in="eth",
        token_out="0x3333333333333333333333333333333333333333",
        amount_in=1,
        allowed_tokens_in=["0x2222222222222222222222222222222222222222"],
        allowed_tokens_out=["0x3333333333333333333333333333333333333333"],
        max_input_per_tx=0,
        allow_native_tokens=True,
    )


def test_validate_trade_allows_native_out_when_enabled() -> None:
    service = PolicyService()

    service.validate_trade(
        vault_address="0x1111111111111111111111111111111111111111",
        recipient="0x1111111111111111111111111111111111111111",
        token_in="0x2222222222222222222222222222222222222222",
        token_out="native",
        amount_in=1,
        allowed_tokens_in=["0x2222222222222222222222222222222222222222"],
        allowed_tokens_out=["0x3333333333333333333333333333333333333333"],
        max_input_per_tx=0,
        allow_native_tokens=True,
    )
