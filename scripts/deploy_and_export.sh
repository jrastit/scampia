#!/usr/bin/env bash
set -euo pipefail

python3 scripts/export_abi.py
python3 scripts/deploy_vault.py
