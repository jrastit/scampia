from typing import Iterable
from app.config import settings

class PolicyViolation(Exception):
    pass


class PolicyService:
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
    ) -> None:
        if vault_address.lower() != recipient.lower():
            raise PolicyViolation("recipient must be the Vault address")

        normalized_allowed_in = {t.lower() for t in allowed_tokens_in if t}
        normalized_allowed_out = {t.lower() for t in allowed_tokens_out if t}

        if normalized_allowed_in and token_in.lower() not in normalized_allowed_in:
            raise PolicyViolation("token_in is not allowed")

        if normalized_allowed_out and token_out.lower() not in normalized_allowed_out:
            raise PolicyViolation("token_out is not allowed")

        if max_input_per_tx > 0 and amount_in > max_input_per_tx:
            raise PolicyViolation("amount exceeds max_input_per_tx")
        
        # if 
    def validate_parameters(
        self,
        # stop_loss_pct,
        # take_profit_pct,
        # max_slippage_tolerance_pct,
        # max_gas_price_gwei,
        token_price,
        token_in,
        token_out) -> bool:
        stop_loss_pct_permission = 0
        # if stop_loss_pct < stop_loss_pct_permission: à voir pour monitorer ça tout le temps / paramétrer dans le trade uniswap?
        #     return
        # take_profit_pct, pareil pour lui
        get_max_open_positions_permission = 3
        get_open_positions_per_agent = 2
        if get_max_open_positions_permission >= get_open_positions_per_agent:
            return False
        get_safe_sold = 10
        # à voir ce qu'on met ici aussi pour faire la conversion si y'en a une
        get_min_eth_balance = 0.01
        if get_safe_sold-token_price < get_min_eth_balance:
            return False
        # max_slippage_tolerance_pct, jsp
        # max_gas_price_gwei, jsp
        authorized_tokens = settings.authorized_tokens
        is_using_authorized_token = False
        for tokens in authorized_tokens:
            if token_in == authorized_tokens[tokens] or token_out == authorized_tokens[tokens]:
                is_using_authorized_token = True
        if is_using_authorized_token == False:
            return False

        return True