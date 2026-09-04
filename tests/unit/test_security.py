"""Unit tests for AirSense security, token hashing, and administrative authorization."""

import pytest
from apps.api.core.security import generate_secure_token, hash_token


def test_token_generation():
    token = generate_secure_token()
    assert token.startswith("airsense_dev_")
    assert len(token) > 30


def test_token_hashing_consistency():
    token = "airsense_dev_test123"
    h1 = hash_token(token)
    h2 = hash_token(token)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex string


def test_token_hashing_uniqueness():
    h1 = hash_token("token_a")
    h2 = hash_token("token_b")
    assert h1 != h2
