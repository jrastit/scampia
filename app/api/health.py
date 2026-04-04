from fastapi import APIRouter


def build_router(settings) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health")
    def health():
        return {
            "ok": True,
            "app": settings.app_name,
            "network": settings.network,
            "chainId": settings.chain_id,
            "safeTxServiceBase": settings.safe_tx_service_base,
        }

    return router
