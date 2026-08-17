#!/usr/bin/env python3
"""
Ergo Anchor Verification Tool — RustChain Bounty (100 RTC)
Validates Blake2b256 commitment hashes from RustChain miner attestation
anchors stored in Ergo blockchain registers (R4-R9).
"""

import hashlib
import json
import sys
import time
from typing import Optional, Tuple, Dict

def blake2b256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()

def blake2b256_hex(data: bytes) -> str:
    return blake2b256(data).hex()

class ErgoRegister:
    def __init__(self, register_id: int, data: bytes):
        self.register_id = register_id
        self.raw = data
    def get_bytes(self, offset: int, length: int) -> bytes:
        if offset + length > len(self.raw):
            raise ValueError(f"Register R{self.register_id}: offset {offset}+{length} exceeds data length {len(self.raw)}")
        return self.raw[offset:offset + length]
    def get_int(self, offset: int, length: int, endian: str = 'big') -> int:
        return int.from_bytes(self.get_bytes(offset, length), endian)
    def get_hex(self, offset: int, length: int) -> str:
        return self.get_bytes(offset, length).hex()

class AttestationAnchor:
    def __init__(self, registers: Dict[int, ErgoRegister]):
        self.registers = registers
        self.miner_id = None
        self.timestamp = None
        self.block_height = None
        self.commitment_hash = None
        self.miner_pubkey_hash = None
        self.signature = None
        self._parse()
    def _parse(self):
        r4 = self.registers.get(4)
        if r4: self.miner_id = r4.get_hex(0, 32)
        r5 = self.registers.get(5)
        if r5:
            self.timestamp = r5.get_int(0, 8)
            self.block_height = r5.get_int(8, 8)
        r6 = self.registers.get(6)
        if r6: self.commitment_hash = r6.get_hex(0, 32)
        r7 = self.registers.get(7)
        if r7: self.miner_pubkey_hash = r7.get_hex(0, 32)
        r8 = self.registers.get(8)
        if r8: self.signature = r8.raw
    def compute_commitment_hash(self) -> str:
        parts = []
        if self.registers.get(4): parts.append(self.registers[4].raw)
        if self.registers.get(5): parts.append(self.registers[5].raw)
        if self.registers.get(7): parts.append(self.registers[7].raw)
        if not parts: raise ValueError("No register data available to compute commitment")
        return blake2b256_hex(b''.join(parts))
    def verify(self) -> Tuple[bool, str]:
        issues = []
        valid = True
        if self.commitment_hash is None: valid = False; issues.append("Missing commitment hash (R6)")
        elif self.miner_id is None: valid = False; issues.append("Missing miner ID (R4)")
        elif self.timestamp is None: valid = False; issues.append("Missing timestamp (R5)")
        elif self.miner_pubkey_hash is None: valid = False; issues.append("Missing miner pubkey hash (R7)")
        else:
            computed = self.compute_commitment_hash()
            if computed != self.commitment_hash: valid = False; issues.append(f"Commitment hash MISMATCH: computed={computed}, stored={self.commitment_hash}")
        if self.timestamp is not None:
            current = int(time.time() * 1000)
            drift = abs(current - self.timestamp)
            if drift > 365 * 24 * 3600 * 1000: valid = False; issues.append(f"Timestamp drift too large: {drift}ms")
        if self.block_height is not None and self.block_height < 0: valid = False; issues.append(f"Negative block height: {self.block_height}")
        if valid: return (True, "VALID: All checks passed. Commitment hash verified.")
        else: return (False, "INVALID: " + "; ".join(issues))
    def report(self) -> str:
        lines = ["=== Ergo Anchor Verification Report ===",
                 f" registers: R4-R9",
                 f" miner_id: {self.miner_id or 'MISSING'}",
                 f" timestamp: {self.timestamp or 'MISSING'}",
                 f" block_height: {self.block_height or 'MISSING'}",
                 f" commitment_hash (R6): {self.commitment_hash or 'MISSING'}",
                 f" miner_pubkey_hash (R7): {self.miner_pubkey_hash or 'MISSING'}",
                 f" signature (R8): {self.signature[:16].hex() + '...' if self.signature else 'MISSING'}",
                 ""]
        if self.commitment_hash:
            try:
                computed = self.compute_commitment_hash()
                lines.append(f" computed_commitment: {computed}")
                lines.append(f" hash_match: {'YES' if computed == self.commitment_hash else 'NO'}")
            except Exception as e:
                lines.append(f" computed_commitment: ERROR - {e}")
        valid, msg = self.verify()
        lines.append("")
        lines.append(f" RESULT: {'VALID' if valid else 'INVALID'}")
        lines.append(f" {msg}")
        return '\n'.join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Ergo Anchor Verification Tool - RustChain Bounty')
    parser.add_argument('--register', '-r', action='append', help='Register data as HEX: R4=<hex>')
    parser.add_argument('--registers-file', '-f', help='JSON file with register data')
    parser.add_argument('--verify-only', action='store_true', help='Only verify')
    args = parser.parse_args()
    registers = {}
    if args.register:
        for spec in args.register:
            if '=' not in spec: print(f"Error: invalid spec: {spec}", file=sys.stderr); sys.exit(1)
            reg_id_str, hex_data = spec.split('=', 1)
            try: reg_num = int(reg_id_str[1:])
            except ValueError: print(f"Error: invalid register ID: {reg_id_str}", file=sys.stderr); sys.exit(1)
            try: data = bytes.fromhex(hex_data)
            except ValueError: print(f"Error: invalid hex for {spec}", file=sys.stderr); sys.exit(1)
            registers[reg_num] = ErgoRegister(reg_num, data)
    if args.registers_file:
        try:
            with open(args.registers_file) as f: reg_data = json.load(f)
            for reg_id_str, hex_data in reg_data.items():
                reg_num = int(reg_id_str)
                data = bytes.fromhex(hex_data)
                registers[reg_num] = ErgoRegister(reg_num, data)
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            print(f"Error reading register file: {e}", file=sys.stderr); sys.exit(1)
    if not registers:
        print("Error: no register data provided.", file=sys.stderr); sys.exit(1)
    anchor = AttestationAnchor(registers)
    if args.verify_only:
        valid, msg = anchor.verify()
        print(f"VERIFICATION: {'PASS' if valid else 'FAIL'}")
        print(msg)
        sys.exit(0 if valid else 1)
    else:
        print(anchor.report())
        valid, _ = anchor.verify()
        sys.exit(0 if valid else 1)

if __name__ == '__main__':
    main()
