from guardian.core.dependencies import get_single_user_id
from guardian.core.user_manager import get_or_create_default_user


def get_test_user_id() -> str:
    try:
        user = get_or_create_default_user()
        user_id = str(user.get("id") or "").strip()
        if user_id:
            return user_id
    except Exception:
        pass
    return get_single_user_id()
