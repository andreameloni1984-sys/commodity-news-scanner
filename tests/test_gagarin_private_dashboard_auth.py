import hashlib

from cloud_api import _session_token, _valid_app_session, _verify_app_password


def test_signed_dashboard_session_is_valid_and_expires():
    secret = "test-secret-with-enough-entropy"
    token = _session_token(secret, 1700000000)
    assert _valid_app_session(token, secret, 1700000100)
    assert not _valid_app_session(token, secret, 1700000000 + 12 * 60 * 60 + 1)
    assert not _valid_app_session(token, "wrong-secret", 1700000100)


def test_password_hash_verification():
    salt = b"0123456789abcdef"
    rounds = 200000
    digest = hashlib.pbkdf2_hmac("sha256", b"correct horse battery staple", salt, rounds)
    encoded = "pbkdf2_sha256$%d$%s$%s" % (rounds, salt.hex(), digest.hex())
    assert _verify_app_password("correct horse battery staple", encoded)
    assert not _verify_app_password("wrong password", encoded)
    assert not _verify_app_password("correct horse battery staple", "invalid")
