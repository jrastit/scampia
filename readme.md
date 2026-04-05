# Scampia Vault Layer

Secure on-chain custody and trading control for AI agents, based on a singleton multi-vault smart contract.

## Overview

Scampia now uses one deployed contract (`ScampiaVault`) that manages many vaults (`vaultId`).

- Each vault has an owner.
- The vault owner sets an owner fee rate (`ownerFeeBps`).
- A manager fee rate (`managerFeeBps`) is set globally by admin.
- Non-owner users pay fees only on realized profit at withdraw.
- Trading operations are restricted to admin (backend signer).
- API keys remain off-chain in backend services.

## Core model

1. Deploy singleton contract once.
2. Create a vault (`createVault`) per owner.
3. Users deposit assets into a specific `vaultId`.
4. Admin executes trades for that `vaultId` through whitelisted targets.
5. Users withdraw shares from that `vaultId`.

Fee behavior at withdraw for non-owner users:

- `profit = max(grossAssets - releasedPrincipal, 0)`
- `ownerFee = profit * ownerFeeBps / 10000`
- `managerFee = profit * managerFeeBps / 10000`
- user receives `grossAssets - ownerFee - managerFee`

## API routes

Base prefix: `/api`

### Health

- `GET /health`

### Vaults

- `GET /v1/vaults`
- `GET /v1/vaults/{vault_id}`
- `POST /v1/vaults/import`
- `GET /v1/vaults/balances`
- `GET /v1/vaults/balance/{token_address}`
- `POST /v1/vaults/create/build`
- `POST /v1/vaults/deposit/build`
- `POST /v1/vaults/withdraw/build`
- `POST /v1/vaults/agent-swap/build`
- `POST /v1/vaults/agent-swap/execute`
- `GET /v1/vaults/{vault_id}/positions/{user_address}`

`GET /v1/vaults` response shape:

```json
{
	"items": [
		{
			"vault_id": 12,
			"owner": "0x...",
			"owner_fee_bps": 300,
			"asset_token": "0x...",
			"total_assets": "123450000000000000000",
			"total_shares": "120000000000000000000"
		}
	]
}
```

`GET /v1/vaults/{vault_id}` response shape:

```json
{
	"vault_id": 12,
	"owner": "0x...",
	"owner_fee_bps": 300,
	"manager_fee_bps": 200,
	"asset_token": "0x...",
	"total_assets": "123450000000000000000",
	"total_shares": "120000000000000000000",
	"created_at": "2026-04-05T12:00:00Z"
}
```

### Users

- `POST /v1/users/connect`
- `GET /v1/users/{wallet_address}`
- `GET /v1/users/{wallet_address}/investments`
- `GET /v1/users`

`GET /v1/users/{wallet_address}/investments` response shape:

```json
{
	"wallet_address": "0x...",
	"items": [
		{
			"vault_id": 12,
			"shares": "1000000000000000000",
			"value": "1020000000000000000",
			"profit": "20000000000000000"
		}
	]
}
```

### ENS

- `GET /v1/ens/config`
- `POST /v1/ens/config/build`
- `POST /v1/ens/config/sync`
- `POST /v1/ens/vaults/register/build`
- `POST /v1/ens/vaults/register`
- `PUT /v1/ens/vaults/policy/build`
- `PUT /v1/ens/vaults/{vault_id}/policy`
- `GET /v1/ens/vaults/{vault_id}`
- `GET /v1/ens/names/{name}`

### Trades

- `POST /v1/trades/quote`
- `POST /v1/trades/build`
- `POST /v1/trades/prepare-vault-tx`
- `POST /v1/trades/prepare-safe-tx` (compat alias)
- `POST /v1/trades/execute-vault-swap`

## Quick local run

```bash
. ./.venv/bin/activate
set -a && . ./.env && set +a
./run.sh
```

Health check:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

## Contract artifacts

Export ABI and bytecode:

```bash
python3 scripts/export_abi.py
```

Artifacts generated:

- `contracts/artifacts/ScampiaVault.abi.json`
- `contracts/artifacts/ScampiaVault.bytecode.txt`

## Contract deployment

Required environment variables:

- `RPC_URL`
- `BACKEND_PRIVATE_KEY`
- `VAULT_ASSET_TOKEN`
- `VAULT_MANAGER_RECIPIENT`
- `VAULT_MANAGER_FEE_BPS`

Deploy:

```bash
python3 scripts/deploy_vault.py
```

One-shot export + deploy:

```bash
bash scripts/deploy_and_export.sh
```

## Configuration

Main runtime configuration sources:

- `.env`
- `app/settings.yaml`

Important vault variables:

- `VAULT_ADDRESS`
- `VAULT_MANAGER_ADDRESS`
- `VAULT_ASSET_TOKEN`
- `VAULT_MANAGER_FEE_BPS`

Important ENS variables for write endpoints:

- `ENS_REGISTRY_ADDRESS`
- `ENS_PUBLIC_RESOLVER_ADDRESS`
- `ENS_PARENT_NAME`
- `BACKEND_PRIVATE_KEY` or `ENS_PRIVATE_KEY` (required for `/v1/ens/*` write operations)

## Tests

### Solidity tests (Foundry)

Install dependency library:

```bash
forge install foundry-rs/forge-std
```

Run tests:

```bash
forge test
```

### API tests (pytest)

```bash
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest -q tests
```

Current automated API suite covers health, vault routes, trades routes, users routes, and ENS routes.

## Notes

- Uniswap quote/build may require a Permit2 signature (`permit_signature`) depending on returned `permitData`.
- Trade API base is normalized to avoid duplicated `/v1`.
- Rate limiting (`429`) is retried with exponential backoff.
