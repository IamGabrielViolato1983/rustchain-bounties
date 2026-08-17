# Ergo Anchor Verification Tool

**RustChain Bounty: Ergo Anchor Verification Tool (100 RTC)**

**Claimed by:** gaussagent (Moltbook agent) - https://www.moltbook.com/u/gaussagent
**Builder:** Felipe Violato
**Wallet:** 0xcAd9A21C94Ca73F6C2F33594BD1E041C7eE2e894 (Base)

## What It Does

Validates Blake2b256 commitment hashes from RustChain miner attestation anchors stored in Ergo blockchain registers (R4-R9).

## Usage

```bash
python ergo_anchor_verifier.py -r R4=<hex> -r R5=<hex> -r R6=<hex> -r R7=<hex>
python ergo_anchor_verifier.py -f test_registers.json
python ergo_anchor_verifier.py --verify-only -f test_registers.json
```

## Features

- Parses Ergo registers R4-R9
- Extracts miner_id, timestamp, block_height, commitment_hash, pubkey_hash, signature
- Computes Blake2b256 commitment from R4+R5+R7 data
- Compares computed hash with stored hash in R6
- Timestamp sanity check (drift > 1 year = invalid)
- Block height validation
- Full verification report with hash match status
- Stdlib-only (Python 3, no external dependencies)

## Test Results

Created test registers with known data. Computed commitment matches stored commitment. Hash match: YES. Result: VALID.

## Files

- `ergo_anchor_verifier.py` - Main verification tool
- `README.md` - This file
