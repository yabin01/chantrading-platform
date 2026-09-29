# ChanTrading Platform — Historical Migration Manifest v1.0

## Purpose

This manifest defines the migration boundary between historical project artifacts and the current engineering tree.

## Source of Truth

Historical specifications and release artifacts are migrated from the project Library/Project materials. Historical content must remain semantically unchanged during archival.

## Version Lineage

- v1.x — foundational ChanLun structural specifications
- v2.x — structural engines and decision architecture
- v3.2.x — Decision Engine and rule freeze
- v3.3.x — stop, sizing, liquidation guard
- v3.4.x — execution, order management, reconciliation, MPC/signing
- v3.5.x — event schema, state store, deterministic replay
- v3.6.0 — production runtime architecture
- v3.7.x — validation engines and JEV safety
- v3.8.x — historical replay and conformance
- v3.9.x — ETH-USD replay, attribution, execution realism and trade ledger
- v4.0.x — paper trading runtime
- v4.1.x — paper control plane and analytics
- v4.2.0 — testnet execution gateway
- v4.2.1 — testnet certification and QA

## Migration Rules

1. Archive historical artifacts before refactoring them.
2. Never silently rewrite historical specifications.
3. Keep architecture rules separate from tunable parameters.
4. Keep deterministic ChanLun geometry separate from LLM/Copilot functions.
5. Preserve source terminology.
6. Mark unresolved version conflicts explicitly.
7. Do not treat an index or manifest as proof that an artifact has been uploaded; each artifact requires a concrete repository path or release asset.

## Current Status

The repository contains the current v4.1.x–v4.2.1 engineering material plus source-derived historical architecture documents. Full historical artifact transfer remains an incremental migration task.
