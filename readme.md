# OpenClaw Safe Layer

> Secure onchain custody and trade validation for AI agents.

## Overview

OpenClaw provides secure onchain skills for user-owned agents. Each agent can have an ENS identity that resolves to the user's Safe smart account. Trades are built through Uniswap and constrained by Zodiac permissions before execution through the Safe.

The **Safe Layer** acts as the security and control middleware between the AI agent and the blockchain. It protects funds, enforces permissions, and validates every trade request before any onchain execution.

## Architecture

<p align="center">
  <img src="./architecture.svg" alt="OpenClaw Safe Layer Architecture" width="680"/>
</p>

## Transaction flow

1. **Trade request** — The OpenClaw agent sends a trade intention (e.g. "swap 500 USDC → ETH")
2. **Balance check** — The Safe Layer verifies the vault holds enough funds
3. **Permission check** — Zodiac Roles module enforces: max amount, max trades/day, whitelisted contracts and tokens
4. **Validation** — If all checks pass, the transaction is built and executed through the Safe. If rejected, the reason is logged
5. **Execution** — The swap is sent to Uniswap via the Safe smart account
6. **Result** — The front displays the transaction, updated balances, and agent performance

## Safe Layer responsibilities

### Balance controls
- Token balance verification before each trade
- Available liquidity tracking
- Minimum / maximum amount enforcement
- Reserved funds management

### Permission controls (Zodiac Roles)
- Agent authorization (enabled / disabled)
- Protocol whitelist (e.g. Uniswap Router only)
- Function whitelist (e.g. `exactInputSingle` only)
- Token pair whitelist

### Risk controls
- Max amount per trade
- Max daily volume per agent
- Max number of trades per day
- Max exposure per agent (% of vault)
- Emergency stop

### Technical controls
- Transaction well-formed
- Slippage within bounds
- Deadline valid
- Target contract matches whitelist