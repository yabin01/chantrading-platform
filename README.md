# ChanLun 1M Trading Agent Platform

A deterministic 1-minute ChanLun trading-agent engineering platform for crypto markets.

## Architecture

Market Data → ChanLun State → Decision Engine → Risk → Order Manager → Execution Gateway → Exchange Adapter

Supporting layers:
- Event Schema / State Store / Deterministic Replay
- Production Runtime / Control Plane
- Performance / Risk / ChanLun Research Analytics
- Paper Execution / Testnet Execution / Certification
- MPC Signing Gateway (architecture stage; production implementation pending)

## Current milestone: v4.2.1

The project has moved from architecture specification into implementation and validation. The current gate is Testnet Connector Certification.

### Version map
- v3.2.1 Source Rule Freeze
- v3.3.1 Stop Anchor
- v3.3.2 Stop Trigger
- v3.3.3 Position Sizing
- v3.3.4 Liquidation Guard
- v3.4.x Execution / Order / Reconciliation / MPC architecture
- v3.5.x Event Schema / State Store / Deterministic Replay
- v3.6.0 Production Runtime Architecture
- v4.1.x Control Plane / Performance / Risk / Research Analytics
- v4.2.0 Testnet Execution Gateway
- v4.2.1 Testnet Connector Certification & QA

## Safety boundary

No production endpoint, production private key, withdrawal permission, or real-fund credential belongs in this repository. Testnet must remain isolated from production.

## Next milestones

v4.2.2 Failure Injection & Chaos Execution
v4.2.3 Paper/Testnet Deterministic Equivalence
v4.3 MPC Wallet & Signing Gateway implementation
v4.4 Production Capital Guard
Production Canary
