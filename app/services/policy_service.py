from typing import Iterable


class PolicyViolation(Exception):
    pass


class PolicyService:
    def validate_trade(
        self,
        safe_address: str,
        recipient: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        allowed_tokens_in: Iterable[str],
        allowed_tokens_out: Iterable[str],
        max_input_per_tx: int,
    ) -> None:
        if safe_address.lower() != recipient.lower():
            raise PolicyViolation("recipient must be the Safe address")

        normalized_allowed_in = {t.lower() for t in allowed_tokens_in if t}
        normalized_allowed_out = {t.lower() for t in allowed_tokens_out if t}

        if normalized_allowed_in and token_in.lower() not in normalized_allowed_in:
            raise PolicyViolation("token_in is not allowed")

        if normalized_allowed_out and token_out.lower() not in normalized_allowed_out:
            raise PolicyViolation("token_out is not allowed")

        if max_input_per_tx > 0 and amount_in > max_input_per_tx:
            raise PolicyViolation("amount exceeds max_input_per_tx")
        
        # if 
