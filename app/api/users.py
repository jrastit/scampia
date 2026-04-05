from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session


class ConnectWalletRequest(BaseModel):
    wallet_address: str


def build_router(user_service, get_db) -> APIRouter:
    router = APIRouter(prefix="/v1/users", tags=["users"])

    @router.post("/connect")
    def connect_wallet(req: ConnectWalletRequest, db: Session = Depends(get_db)):
        try:
            return user_service.connect_wallet(db, req.wallet_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{wallet_address}")
    def get_user(wallet_address: str, db: Session = Depends(get_db)):
        user = user_service.get_user(db, wallet_address)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @router.get("/{wallet_address}/investments")
    def get_user_investments(wallet_address: str):
        try:
            return user_service.get_user_investments(wallet_address)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("")
    def list_users(db: Session = Depends(get_db)):
        return user_service.get_all_users(db)

    return router
