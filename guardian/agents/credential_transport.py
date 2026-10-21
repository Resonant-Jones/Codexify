"""Ephemeral encryption for Guardian-to-worker credential lease responses."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_AAD = b"codexify-coding-credential-lease:v1"


def generate_lease_keypair() -> tuple[bytes, bytes]:
    """Return one-use (private PEM, public PEM) key material."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def seal_lease_payload(public_pem: str | bytes, payload: dict[str, Any]) -> dict[str, str]:
    public_key = serialization.load_pem_public_key(
        public_pem.encode("utf-8") if isinstance(public_pem, str) else public_pem
    )
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("worker lease key must be RSA")
    content_key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ciphertext = AESGCM(content_key).encrypt(nonce, plaintext, _AAD)
    wrapped_key = public_key.encrypt(
        content_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=_AAD,
        ),
    )
    return {
        "version": "1",
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "wrapped_key": base64.b64encode(wrapped_key).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def open_lease_payload(private_pem: str | bytes, envelope: dict[str, Any]) -> dict[str, Any]:
    if _text(envelope.get("version")) != "1":
        raise ValueError("unsupported credential lease envelope")
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8") if isinstance(private_pem, str) else private_pem,
        password=None,
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("worker lease key must be RSA")
    content_key = private_key.decrypt(
        base64.b64decode(_text(envelope.get("wrapped_key")), validate=True),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=_AAD,
        ),
    )
    plaintext = AESGCM(content_key).decrypt(
        base64.b64decode(_text(envelope.get("nonce")), validate=True),
        base64.b64decode(_text(envelope.get("ciphertext")), validate=True),
        _AAD,
    )
    value = json.loads(plaintext)
    if not isinstance(value, dict):
        raise ValueError("credential lease payload must be an object")
    return value


def _text(value: Any) -> str:
    return str(value or "").strip()
