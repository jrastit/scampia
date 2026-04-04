try:
	from app.api.vaults import build_router
except ImportError:
	from vaults import build_router
