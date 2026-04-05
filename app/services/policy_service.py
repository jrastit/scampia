from typing import Iterable


class PolicyViolation(Exception):
    pass


class PolicyService:
    _NATIVE_TOKEN_SENTINELS = {
        "eth",
        "native",
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "0x0000000000000000000000000000000000000000",
    }

    @classmethod
    def _is_native_token_ref(cls, token: str) -> bool:
        normalized = (token or "").strip().lower()
        return normalized in cls._NATIVE_TOKEN_SENTINELS

    def validate_trade(
        self,
        vault_address: str,
        recipient: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        allowed_tokens_in: Iterable[str],
        allowed_tokens_out: Iterable[str],
        max_input_per_tx: int,
        allow_native_tokens: bool = False,
    ) -> None:
        if vault_address.lower() != recipient.lower():
            raise PolicyViolation("recipient must be the Vault address")

        token_in_is_native = self._is_native_token_ref(token_in)
        token_out_is_native = self._is_native_token_ref(token_out)

        if token_in_is_native and not allow_native_tokens:
            raise PolicyViolation("native token is not supported as token_in; use wrapped token address (e.g. WETH)")

        if token_out_is_native and not allow_native_tokens:
            raise PolicyViolation("native token is not supported as token_out; use wrapped token address (e.g. WETH)")

        normalized_allowed_in = {t.lower() for t in allowed_tokens_in if t}
        normalized_allowed_out = {t.lower() for t in allowed_tokens_out if t}

        if normalized_allowed_in and not token_in_is_native and token_in.lower() not in normalized_allowed_in:
            raise PolicyViolation("token_in is not allowed")

        if normalized_allowed_out and not token_out_is_native and token_out.lower() not in normalized_allowed_out:
            raise PolicyViolation("token_out is not allowed")

        if max_input_per_tx > 0 and amount_in > max_input_per_tx:
            raise PolicyViolation("amount exceeds max_input_per_tx")
