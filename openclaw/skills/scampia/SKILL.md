---
name: scampia-api
description: Utilise l'API Scampia pour connecter un wallet, consulter des utilisateurs, vaults, ENS et trades, puis construire/exécuter les requêtes HTTP vers le backend Scampia.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🏦"
    homepage: "https://scampia.fexhu.com:20443/"
    primaryEnv: SCAMPIA_BASE_URL
    requires:
      env:
        - SCAMPIA_BASE_URL
      bins:
        - curl
    config:
      baseUrlEnv: SCAMPIA_BASE_URL
      bearerTokenEnv: SCAMPIA_API_KEY
---

# Scampia API Skill

Utilise ce skill quand l'utilisateur veut interagir avec l'API **Scampia Vault Layer** : santé du service, connexion wallet, lecture utilisateur, lecture vault, sync ENS, devis/build/exécution de trade, préparation Safe TX, etc.

## But

Ce skill transforme une intention métier en appel HTTP vers l'API Scampia.

Base API attendue :

- `SCAMPIA_BASE_URL` = origine du backend, par exemple `https://scampia.fexhu.com:20443/#/`
- Le préfixe OpenAPI est déjà `/api`
- Exemple d'URL finale : `$SCAMPIA_BASE_URL/api/v1/vaults`

Authentification :

- La plupart des routes montrées ici sont publiques côté spec.
- **`POST /v1/trades/prepare-safe-tx` requiert un Bearer token**.
- Si `SCAMPIA_API_KEY` est défini, envoie l'en-tête `Authorization: Bearer $SCAMPIA_API_KEY`.
- Ne jamais afficher ni logger la valeur du token.

## Règles d'exécution

1. Vérifier que `SCAMPIA_BASE_URL` est défini.
2. Construire les URL avec le préfixe fixe `/api`.
3. Pour les `POST`/`PUT`, envoyer `Content-Type: application/json`.
4. Pour `prepare-safe-tx`, ajouter `Authorization: Bearer ...`.
5. En cas d'erreur `422`, résumer clairement les champs invalides retournés par l'API.
6. En cas de `429`, réessayer avec backoff exponentiel court.
7. Toujours préférer les endpoints de lecture avant les endpoints de mutation si l'utilisateur demande d'abord une vérification.
8. Pour les montants, conserver les valeurs comme chaînes si l'API les attend en string.
9. Ne jamais inventer d'adresse, `vault_id`, `chain_id`, signature ou token.
10. Pour les opérations sensibles on-chain (`execute`, `register`, `policy`, `sync`, `build`), reformuler brièvement les paramètres avant l'appel si l'intention utilisateur n'est pas explicite.

## Helper shell recommandé

```bash
scampia_api() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url="${SCAMPIA_BASE_URL%/}/api${path}"

  if [ -n "$body" ]; then
    curl -sS -X "$method" \
      -H "Content-Type: application/json" \
      ${SCAMPIA_API_KEY:+-H "Authorization: Bearer $SCAMPIA_API_KEY"} \
      "$url" \
      --data "$body"
  else
    curl -sS -X "$method" \
      ${SCAMPIA_API_KEY:+-H "Authorization: Bearer $SCAMPIA_API_KEY"} \
      "$url"
  fi
}
```

## Mapping intentions → endpoints

### Health

- Vérifier la santé du backend → `GET /health`

```bash
curl -sS "$SCAMPIA_BASE_URL/api/health"
```

### Users

- Connecter un wallet → `POST /v1/users/connect`
- Lire un user → `GET /v1/users/{wallet_address}`
- Lire l'état de sync vault → `GET /v1/users/{wallet_address}/vault-sync`
- Lire les investissements → `GET /v1/users/{wallet_address}/investments`
- Lister les users → `GET /v1/users`
- Récupérer le fichier de config signé → `POST /v1/users/config`

Exemples :

```bash
scampia_api POST /v1/users/connect '{"wallet_address":"0xabc..."}'
```

```bash
scampia_api GET /v1/users/0xabc...
```

```bash
scampia_api GET /v1/users/0xabc.../vault-sync
```

```bash
scampia_api GET /v1/users/0xabc.../investments
```

```bash
scampia_api POST /v1/users/config '{"wallet_address":"0xabc...","api_key_signed":"0xsig..."}'
```

### Vaults

- Lister les vaults → `GET /v1/vaults`
- Détails d'un vault → `GET /v1/vaults/{vault_id}`
- Importer un vault → `POST /v1/vaults/import`
- Soldes globaux du vault layer → `GET /v1/vaults/balances`
- Solde d'un token → `GET /v1/vaults/balance/{token_address}`
- Allowance de dépôt → `GET /v1/vaults/{vault_id}/deposit/allowance/{owner_address}?amount=...`
- Construire création de vault → `POST /v1/vaults/create/build`
- Construire dépôt → `POST /v1/vaults/deposit/build`
- Construire retrait → `POST /v1/vaults/withdraw/build`
- Construire agent swap → `POST /v1/vaults/agent-swap/build`
- Exécuter agent swap → `POST /v1/vaults/agent-swap/execute`
- Position user dans un vault → `GET /v1/vaults/{vault_id}/positions/{user_address}`

Exemples :

```bash
scampia_api GET /v1/vaults
```

```bash
scampia_api GET /v1/vaults/12
```

```bash
scampia_api POST /v1/vaults/import '{"vault_address":"0xvault...","chain_id":11155111}'
```

```bash
scampia_api GET '/v1/vaults/12/deposit/allowance/0xowner...?amount=1000000'
```

```bash
scampia_api POST /v1/vaults/create/build '{"owner_fee_bps":300}'
```

```bash
scampia_api POST /v1/vaults/deposit/build '{"vault_id":12,"amount":"1000000000000000000","receiver":"0xreceiver..."}'
```

```bash
scampia_api POST /v1/vaults/withdraw/build '{"vault_id":12,"shares":"1000000000000000000","receiver":"0xreceiver..."}'
```

```bash
scampia_api POST /v1/vaults/agent-swap/build '{"vault_id":12,"target":"0xtarget...","data":"0xdeadbeef","min_asset_delta":"0","value":"0"}'
```

```bash
scampia_api POST /v1/vaults/agent-swap/execute '{"vault_id":12,"target":"0xtarget...","data":"0xdeadbeef","min_asset_delta":"0","value":"0"}'
```

```bash
scampia_api GET /v1/vaults/12/positions/0xuser...
```

### ENS

- Lire config ENS → `GET /v1/ens/config`
- Construire tx config ENS → `POST /v1/ens/config/build`
- Sync config ENS → `POST /v1/ens/config/sync`
- Construire register ENS d'un vault → `POST /v1/ens/vaults/register/build`
- Enregistrer ENS d'un vault → `POST /v1/ens/vaults/register`
- Construire tx policy ENS → `PUT /v1/ens/vaults/policy/build`
- Définir policy ENS → `PUT /v1/ens/vaults/{vault_id}/policy`
- Lire le profil ENS d'un vault → `GET /v1/ens/vaults/{vault_id}`
- Lire un profil ENS par nom → `GET /v1/ens/names/{name}`

Exemples :

```bash
scampia_api GET /v1/ens/config
```

```bash
scampia_api POST /v1/ens/config/build '{"registry_address":"0xregistry...","resolver_address":"0xresolver..."}'
```

```bash
scampia_api POST /v1/ens/vaults/register/build '{"vault_id":12,"label":"alpha"}'
```

```bash
scampia_api POST /v1/ens/vaults/register '{"vault_id":12,"label":"alpha"}'
```

```bash
scampia_api PUT /v1/ens/vaults/policy/build '{"vault_id":12,"stop_loss_pct":5.0,"take_profit_pct":15.0}'
```

```bash
scampia_api PUT /v1/ens/vaults/12/policy '{"stop_loss_pct":5.0,"take_profit_pct":15.0,"authorized_tokens":["0xtoken..."]}'
```

```bash
scampia_api GET /v1/ens/vaults/12
```

```bash
scampia_api GET /v1/ens/names/alpha.scampia.eth
```

### Trades

- Demander un quote → `POST /v1/trades/quote`
- Construire un trade → `POST /v1/trades/build`
- Préparer une Safe TX → `POST /v1/trades/prepare-safe-tx` **(Bearer requis)**
- Exécuter un vault swap → `POST /v1/trades/execute-vault-swap`

Exemples :

```bash
scampia_api POST /v1/trades/quote '{"chain_id":11155111,"token_in":"0xTokenIn...","token_out":"0xTokenOut...","amount_in":"1000000","slippage_bps":50}'
```

```bash
scampia_api POST /v1/trades/build '{"chain_id":11155111,"vault_id":12,"token_in":"0xTokenIn...","token_out":"0xTokenOut...","amount_in":"1000000","slippage_bps":50}'
```

```bash
scampia_api POST /v1/trades/prepare-safe-tx '{"chain_id":11155111,"vault_id":12,"safe_address":"0xsafe...","token_in":"0xTokenIn...","token_out":"0xTokenOut...","amount_in":"1000000","slippage_bps":50}'
```

```bash
scampia_api POST /v1/trades/execute-vault-swap '{"chain_id":11155111,"vault_id":12,"token_in":"0xTokenIn...","token_out":"0xTokenOut...","amount_in":"1000000","slippage_bps":50}'
```

## Schémas importants

### Connect wallet

```json
{"wallet_address":"0x..."}
```

### Build trade

```json
{
  "chain_id": 11155111,
  "vault_id": 12,
  "vault_address": null,
  "safe_address": null,
  "token_in": "0x...",
  "token_out": "0x...",
  "amount_in": "1000000",
  "slippage_bps": 50,
  "permit_signature": null,
  "recipient": null
}
```

### Deposit request

```json
{
  "vault_id": 12,
  "amount": "1000000000000000000",
  "receiver": "0x..."
}
```

### Withdraw request

```json
{
  "vault_id": 12,
  "shares": "1000000000000000000",
  "receiver": "0x..."
}
```

## Gestion des réponses utiles

### Réponses de lecture à résumer

- `GET /v1/vaults` → résumer `vault_id`, `owner`, `asset_token`, `total_assets`, `total_shares`
- `GET /v1/vaults/{vault_id}` → ajouter `owner_fee_bps`, `manager_fee_bps`, `created_at`
- `GET /v1/users/{wallet_address}` → résumer `vault_id`, `pending_sync`, `network`, `chain_id`, `is_active`
- `GET /v1/users/{wallet_address}/investments` → résumer chaque `vault_id`, `shares`, `value`, `profit`
- `GET /v1/vaults/{vault_id}/positions/{user_address}` → résumer `shares`, `principal`, `estimatedAssets`

### États métier à reconnaître

- `pending_sync=true` + `retry_after_seconds>0` → informer que l'indexation on-chain n'est pas terminée.
- `sync_source=global_latest` → signaler que le `vault_id` est un fallback global et pas un match propriétaire confirmé.
- Présence de `permitData` dans une réponse trade → informer qu'une signature Permit2 peut être nécessaire avant l'exécution.

## Sécurité

- Ne jamais exposer `SCAMPIA_API_KEY`, `BACKEND_PRIVATE_KEY`, `ENS_PRIVATE_KEY`.
- Ne jamais prétendre qu'une transaction on-chain est finalisée si l'API ne le confirme pas.
- Pour les opérations d'écriture ENS, de swap ou d'exécution, traiter le résultat JSON de l'API comme source de vérité.
- Si l'utilisateur demande de "simuler" ou "préparer", utiliser les endpoints `build` ou `quote` avant `execute`.

## Diagnostic rapide

```bash
curl -sS "$SCAMPIA_BASE_URL/api/health"
```

Attendu :

- `ok: true`
- `app`
- `network`
- `chainId`
- `safeTxServiceBase`

## Quand utiliser ce skill

Active ce skill si la demande mentionne :

- Scampia
- vault / vaults
- connect wallet
- ENS vault profile / ENS config
- deposit / withdraw / shares
- quote / trade / safe tx / vault swap
- user investments / vault sync

## Quand ne pas l'utiliser

- Si la demande concerne la logique Solidity interne sans appel API.
- Si la demande porte seulement sur de la documentation générale sans exécution de requête.
- Si l'utilisateur n'a fourni ni base URL utilisable ni contexte local permettant d'appeler le backend.
