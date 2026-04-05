from fastapi import APIRouter, HTTPException

try:
    from app.schemas import (
        BuildVaultEnsPolicyTxRequest,
        RegisterVaultEnsRequest,
        SetEnsConfigRequest,
        VaultEnsPolicyUpdateRequest,
    )
    from app.services.ens_service import namehash
except ImportError:
    from schemas import (
        BuildVaultEnsPolicyTxRequest,
        RegisterVaultEnsRequest,
        SetEnsConfigRequest,
        VaultEnsPolicyUpdateRequest,
    )
    from ens_service import namehash


PROFILE_TEXT_KEYS = [
    "stop_loss_pct",
    "take_profit_pct",
    "max_open_positions",
    "min_eth_balance",
    "max_slippage_tolerance_pct",
    "max_gas_price_gwei",
    "authorized_tokens",
]


def build_router(ens_service, _vault_service, settings) -> APIRouter:
    router = APIRouter(prefix="/v1/ens", tags=["ens"])

    @router.get("/config")
    def get_ens_config():
        return {
            "network": settings.network,
            "chainId": settings.chain_id,
            "managerAddress": settings.vault_manager_address or settings.vault_address,
            "parentName": settings.ens_parent_name,
            "parentNode": ens_service.w3.to_hex(namehash(settings.ens_parent_name)),
            "registryAddress": settings.ens_registry_address,
            "publicResolverAddress": settings.ens_public_resolver_address,
        }

    @router.post("/config/build")
    def build_ens_config_tx(req: SetEnsConfigRequest):
        try:
            return ens_service.build_set_config_tx(
                registry_address=req.registry_address,
                resolver_address=req.resolver_address,
                parent_name=req.parent_name,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/config/sync")
    def sync_ens_config(req: SetEnsConfigRequest):
        try:
            return ens_service.set_config(
                registry_address=req.registry_address,
                resolver_address=req.resolver_address,
                parent_name=req.parent_name,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/vaults/register/build")
    def build_register_vault_ens(req: RegisterVaultEnsRequest):
        try:
            return ens_service.build_register_vault_tx(
                vault_id=req.vault_id,
                label=req.label,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/vaults/register")
    def register_vault_ens(req: RegisterVaultEnsRequest):
        try:
            return ens_service.register_vault(
                vault_id=req.vault_id,
                label=req.label,
                texts=req.to_text_records(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/vaults/policy/build")
    def build_vault_policy_tx(req: BuildVaultEnsPolicyTxRequest):
        try:
            return ens_service.build_set_vault_texts_tx(
                vault_id=req.vault_id,
                texts=req.to_text_records(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/vaults/{vault_id}/policy")
    def set_vault_policy(vault_id: int, req: VaultEnsPolicyUpdateRequest):
        try:
            return ens_service.set_vault_text_records(
                vault_id=vault_id,
                texts=req.to_text_records(),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/vaults/{vault_id}")
    def get_vault_ens_profile(vault_id: int):
        try:
            return ens_service.get_vault_profile(vault_id, text_keys=PROFILE_TEXT_KEYS)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/names/{name}")
    def get_ens_profile(name: str):
        try:
            return ens_service.get_profile(name, text_keys=PROFILE_TEXT_KEYS)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
