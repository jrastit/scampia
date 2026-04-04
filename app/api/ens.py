from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from app.schemas import CreateEnsSubnameRequest, UpdateEnsRecordsRequest
except ImportError:
    from schemas import CreateEnsSubnameRequest, UpdateEnsRecordsRequest


class SetReverseEnsRequest(BaseModel):
    address: str
    name: str


class PrepareReverseEnsSafeTxRequest(BaseModel):
    safe_address: str
    address: str
    name: str
    operation: int = 0


class PrepareEnsSubnameSafeTxRequest(BaseModel):
    safe_address: str
    parent_name: str | None = None
    label: str
    owner_address: str | None = None
    resolver_address: str | None = None
    ttl: int = 0
    operation: int = 0


class PrepareSetEnsAddrSafeTxRequest(BaseModel):
    safe_address: str
    name: str
    address: str
    resolver_address: str | None = None
    operation: int = 0


class PrepareSetEnsTextSafeTxRequest(BaseModel):
    safe_address: str
    name: str
    key: str
    value: str
    resolver_address: str | None = None
    operation: int = 0


class RegisterSafeEnsRequest(BaseModel):
    safe_address: str
    label: str
    parent_name: str | None = None
    resolver_address: str | None = None
    ttl: int = 0
    address: str | None = None
    set_reverse: bool = True
    texts: dict[str, str] = Field(default_factory=dict)


def build_router(ens_service, safe_service, settings) -> APIRouter:
    router = APIRouter(prefix="/v1/ens", tags=["ens"])

    @router.post("/reverse")
    def set_reverse_ens(req: SetReverseEnsRequest):
        try:
            return ens_service.set_reverse_name(
                target_address=req.address,
                name=req.name,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/reverse/prepare-safe-tx")
    def prepare_reverse_ens_safe_tx(req: PrepareReverseEnsSafeTxRequest):
        try:
            tx = ens_service.build_set_reverse_name_tx(
                target_address=req.address,
                name=req.name,
            )
            return safe_service.build_safe_tx(
                safe_address=req.safe_address,
                to=tx["to"],
                data=tx["data"],
                value=tx["value"],
                operation=req.operation,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/subnames")
    def create_subname(req: CreateEnsSubnameRequest):
        try:
            resolver = req.resolver_address or settings.ens_public_resolver_address
            if not resolver:
                raise ValueError("resolver_address is required")

            owner = req.owner_address or req.safe_address
            return ens_service.create_subname(
                parent_name=req.parent_name,
                label=req.label,
                owner_address=owner,
                resolver_address=resolver,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/subnames/prepare-safe-tx")
    def prepare_subname_safe_tx(req: PrepareEnsSubnameSafeTxRequest):
        try:
            parent_name = req.parent_name or settings.ens_parent_name
            resolver = req.resolver_address or settings.ens_public_resolver_address
            if not resolver:
                raise ValueError("resolver_address is required")

            owner = req.owner_address or req.safe_address
            tx = ens_service.build_create_subname_tx(
                parent_name=parent_name,
                label=req.label,
                owner_address=owner,
                resolver_address=resolver,
                ttl=req.ttl,
            )
            return safe_service.build_safe_tx(
                safe_address=req.safe_address,
                to=tx["to"],
                data=tx["data"],
                value=tx["value"],
                operation=req.operation,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.put("/records")
    def update_ens_records(req: UpdateEnsRecordsRequest):
        try:
            result = {"name": req.name}
            if req.address:
                result["addr"] = ens_service.set_addr(req.name, req.address)
            if req.texts:
                result["texts"] = ens_service.set_text_records(req.name, req.texts)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/config")
    def get_ens_config():
        return {
            "network": settings.network,
            "chainId": settings.chain_id,
            "parentName": settings.ens_parent_name,
            "registryAddress": settings.ens_registry_address,
            "reverseRegistrarAddress": settings.ens_reverse_registrar_address,
            "publicResolverAddress": settings.ens_public_resolver_address,
        }

    @router.post("/register-safe")
    def register_safe_ens(req: RegisterSafeEnsRequest):
        try:
            parent_name = req.parent_name or settings.ens_parent_name
            resolver = req.resolver_address or settings.ens_public_resolver_address
            if not resolver:
                raise ValueError("resolver_address is required")

            full_name = ens_service.resolve_full_name(req.label, parent_name)
            result = {
                "subname": ens_service.create_subname(
                    parent_name=parent_name,
                    label=req.label,
                    owner_address=req.safe_address,
                    resolver_address=resolver,
                    ttl=req.ttl,
                )
            }

            if req.address:
                result["addr"] = ens_service.set_addr(full_name, req.address, resolver_address=resolver)

            if req.texts:
                result["texts"] = ens_service.set_text_records(full_name, req.texts, resolver_address=resolver)

            if req.set_reverse:
                result["reverse"] = ens_service.set_reverse_name(req.safe_address, full_name)

            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/addr/prepare-safe-tx")
    def prepare_set_ens_addr_safe_tx(req: PrepareSetEnsAddrSafeTxRequest):
        try:
            tx = ens_service.build_set_addr_tx(
                name=req.name,
                address=req.address,
                resolver_address=req.resolver_address,
            )
            return safe_service.build_safe_tx(
                safe_address=req.safe_address,
                to=tx["to"],
                data=tx["data"],
                value=tx["value"],
                operation=req.operation,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/text/prepare-safe-tx")
    def prepare_set_ens_text_safe_tx(req: PrepareSetEnsTextSafeTxRequest):
        try:
            tx = ens_service.build_set_text_tx(
                name=req.name,
                key=req.key,
                value=req.value,
                resolver_address=req.resolver_address,
            )
            return safe_service.build_safe_tx(
                safe_address=req.safe_address,
                to=tx["to"],
                data=tx["data"],
                value=tx["value"],
                operation=req.operation,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/names/{name}")
    def get_ens_profile(name: str):
        try:
            return ens_service.get_profile(
                name,
                text_keys=["agent:type", "agent:capabilities", "agent:api", "agent:safe"],
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
