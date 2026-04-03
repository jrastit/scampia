from typing import Any, Dict, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError

from app.config import settings


class SimulationError(Exception):
    pass


class SimulationService:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))

    def simulate_call(
        self,
        from_address: str,
        to: str,
        data: str,
        value: int = 0,
        block: str = "latest",
    ) -> Dict[str, Any]:
        tx = {
            "from": Web3.to_checksum_address(from_address),
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": value,
        }

        try:
            result = self.w3.eth.call(tx, block_identifier=block)
            return {
                "ok": True,
                "returnData": result.hex(),
            }
        except ContractLogicError as e:
            raise SimulationError(f"simulation reverted: {str(e)}")
        except Exception as e:
            raise SimulationError(f"simulation failed: {str(e)}")