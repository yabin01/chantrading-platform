# Architecture Decisions Preserved from Source Materials

## Deterministic Core Boundary

The ChanLun 1M structural engine is deterministic and remains isolated from external LLMs and exchange-specific execution code.

Core chain:
1m K-lines → Fractal → Strict Bi → Segment → 1m Center → Ai (A0~An) → Same-Level Eligibility → MACD Area Divergence → BUY/HOLD/SELL Arbitration → Fractal Extreme Hard Stop.

## Execution Boundary

DecisionAgent produces a deterministic OrderIntent. RiskEngine validates it before ExecutionEngine. Exchange-specific execution is downstream from the decision core.

## Copilot Boundary

Copilot is read-oriented. It may read Canonical State and ReasonCodes, explain decisions, and compile structured emergency/risk actions. It may not identify geometry, generate independent buy/sell decisions, or call exchange order APIs directly.

## Security Boundary

The source guide specifies a Hyperliquid USDC smart-vault / EIP-712 minimum-permission architecture: an Agent Key is separated from custody authority and must not have withdrawal or cross-address transfer authority.

## Observability Boundary

The source guide specifies SCAN → EVAL → RISK → EXEC → FILL → EXIT event stages, with structured timestamps and ReasonCodes.

## Recovery Boundary

Reconciliation mismatch, failed protection-stop recovery, and excessive data gaps are kill-switch triggers. The runtime enters FROZEN and blocks new BUY decisions.

## Parameter Separation

Architecture rules are frozen. Tunable values such as stop buffer, MACD decay threshold, risk percentage, and timing thresholds belong in configuration/parameter layers and must not be hard-coded into structural logic.
