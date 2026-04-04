from fastapi import FastAPI

try:
    from app.api.ens import build_router as build_ens_router
    from app.api.health import build_router as build_health_router
    from app.api.safes import build_router as build_safes_router
    from app.api.trades import build_router as build_trades_router
    from app.api.users import build_router as build_users_router
    from app.config import settings
    from app.data import get_db, init_db
    from app.services.ens_service import ENSService
    from app.services.policy_service import PolicyService
    from app.services.safe_service import SafeService
    from app.services.simulation_service import SimulationService
    from app.services.trade_service import TradeService
    from app.services.uniswap_service import UniswapService
    from app.services.user_service import UserService
except ImportError:
    from api.ens import build_router as build_ens_router
    from api.health import build_router as build_health_router
    from api.safes import build_router as build_safes_router
    from api.trades import build_router as build_trades_router
    from api.users import build_router as build_users_router
    from config import settings
    from data import get_db, init_db
    from ens_service import ENSService
    from policy_service import PolicyService
    from safe_service import SafeService
    from simulation_service import SimulationService
    from trade_service import TradeService
    from uniswap_service import UniswapService
    from user_service import UserService


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)

init_db()

ens_service = ENSService()
safe_service = SafeService()
uniswap_service = UniswapService()
policy_service = PolicyService()
simulation_service = SimulationService()
trade_service = TradeService(
    uniswap_service=uniswap_service,
    policy_service=policy_service,
    simulation_service=simulation_service,
    safe_service=safe_service,
)
user_service = UserService(safe_service=safe_service)

app.include_router(build_health_router(settings))
app.include_router(build_users_router(user_service, get_db))
app.include_router(build_safes_router(safe_service))
app.include_router(build_ens_router(ens_service, safe_service, settings))
app.include_router(build_trades_router(trade_service, settings))
