"""Checksums and content hashing for records and artifacts."""

from __future__ import annotations

import hashlib
from typing import BinaryIO


E_HASH_ALGORITHM = "SHA-256"


def mos_sha256_bytes(mos_data: bytes) -> str:
    """Return lowercase hex SHA-256 of bytes."""
    return hashlib.sha256(mos_data).hexdigest()


def mos_sha256_stream(mos_stream: BinaryIO, mos_chunk_size: int = 65536) -> str:
    """Stream large payloads without loading entirely into memory."""
    mos_h = hashlib.sha256()
    while True:
        mos_chunk = mos_stream.read(mos_chunk_size)
        if not mos_chunk:
            break
        mos_h.update(mos_chunk)
    return mos_h.hexdigest()


def mos_verify_checksum(mos_content: bytes, mos_expected_hex: str) -> bool:
    """Constant-time friendly compare of digest."""
    return mos_sha256_bytes(mos_content) == mos_expected_hex.lower()
