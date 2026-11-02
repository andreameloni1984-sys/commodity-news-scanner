import hashlib

from cloud_api import (
    _clear_login_failures,
    _login_rate_limit_retry_after,
    _record_login_failure,
    _session_token,
    _valid_app_session,
    _verify_app_password,
)


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



def test_dashboard_login_throttles_after_five_failures_and_expires():
    client_key = "test-throttle-expiry"
    _clear_login_failures(client_key)
    for offset in range(5):
        _record_login_failure(client_key, now=1000.0 + offset)

    assert _login_rate_limit_retry_after(client_key, now=1004.0) == 896
    # The first failure leaves the rolling 15-minute window at t=1900.
    assert _login_rate_limit_retry_after(client_key, now=1900.0) == 0
    _clear_login_failures(client_key)


def test_dashboard_login_throttle_is_per_client_and_success_can_clear_it():
    blocked_client = "test-throttle-client-a"
    other_client = "test-throttle-client-b"
    _clear_login_failures(blocked_client)
    _clear_login_failures(other_client)

    for offset in range(5):
        _record_login_failure(blocked_client, now=2000.0 + offset)

    assert _login_rate_limit_retry_after(blocked_client, now=2005.0) > 0
    assert _login_rate_limit_retry_after(other_client, now=2005.0) == 0

    _clear_login_failures(blocked_client)
    assert _login_rate_limit_retry_after(blocked_client, now=2005.0) == 0
    _clear_login_failures(other_client)
