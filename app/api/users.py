from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.schemas import ConnectWalletResponse, UserInvestmentsResponse, UserResponse, UserVaultSyncResponse


class ConnectWalletRequest(BaseModel):
    wallet_address: str


def build_router(user_service, get_db) -> APIRouter:
    router = APIRouter(prefix="/v1/users", tags=["users"])

    @router.post("/connect", response_model=ConnectWalletResponse)
    def connect_wallet(req: ConnectWalletRequest, db: Session = Depends(get_db)):
        try:
            return user_service.connect_wallet(db, req.wallet_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{wallet_address}", response_model=UserResponse)
    def get_user(wallet_address: str, db: Session = Depends(get_db)):
        user = user_service.get_user(db, wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @router.get("/{wallet_address}/vault-sync", response_model=UserVaultSyncResponse)
    def get_user_vault_sync(wallet_address: str, db: Session = Depends(get_db)):
        payload = user_service.get_user_vault_sync(db, wallet_address)
        if not payload:
            raise HTTPException(status_code=404, detail="User not found")
        return payload

    @router.get("/{wallet_address}/investments", response_model=UserInvestmentsResponse)
    def get_user_investments(wallet_address: str):
        try:
            return user_service.get_user_investments(wallet_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("", response_model=list[UserResponse])
    def list_users(db: Session = Depends(get_db)):
        return user_service.get_all_users(db)

    return router
