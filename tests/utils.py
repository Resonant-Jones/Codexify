import os

TEST_API_KEY = "test-api-key"
_DEFAULT_TEST_USER_ID = "local"


def get_test_user_id() -> str:
    try:
        from guardian.core.user_manager import get_or_create_default_user

        user = get_or_create_default_user()
        user_id = str(user.get("id") or "").strip()
        if user_id:
            return user_id
    except Exception:
        pass
    try:
        from guardian.core.dependencies import get_single_user_id

        return get_single_user_id()
    except Exception:
        configured = (os.getenv("CODEXIFY_SINGLE_USER_ID") or "").strip()
        return configured or _DEFAULT_TEST_USER_ID


def get_test_api_key() -> str:
    return TEST_API_KEY


def get_test_auth_headers(*, user_id: str | None = None) -> dict[str, str]:
    headers = {"X-API-Key": get_test_api_key()}
    if user_id:
        headers["X-User-Id"] = user_id
    return headers
