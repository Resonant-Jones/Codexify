from guardian.core.capability_tokens import (
    CANONICAL_CAPABILITY_IDENTIFIERS,
    CAPABILITY_FAMILIES,
    CAPABILITY_GRANT_KINDS,
    CAPABILITY_GRANT_SCOPES,
    CAPABILITY_GRANT_STATUSES,
    CapabilityFamily,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)


def test_capability_grant_scope_tokens_are_stable() -> None:
    assert CapabilityGrantScope.ACCOUNT.value == "account"
    assert CAPABILITY_GRANT_SCOPES == {"account"}


def test_capability_grant_kind_tokens_are_stable() -> None:
    assert CapabilityGrantKind.PERMANENT.value == "permanent"
    assert CapabilityGrantKind.TIME_BOXED.value == "time_boxed"
    assert CapabilityGrantKind.PROMO.value == "promo"
    assert CapabilityGrantKind.TRIAL.value == "trial"
    assert CAPABILITY_GRANT_KINDS == {
        "permanent",
        "time_boxed",
        "promo",
        "trial",
    }


def test_capability_grant_status_tokens_are_stable() -> None:
    assert CapabilityGrantStatus.ACTIVE.value == "active"
    assert CapabilityGrantStatus.EXPIRED.value == "expired"
    assert CapabilityGrantStatus.REVOKED.value == "revoked"
    assert CapabilityGrantStatus.SUSPENDED.value == "suspended"
    assert CAPABILITY_GRANT_STATUSES == {
        "active",
        "expired",
        "revoked",
        "suspended",
    }


def test_capability_family_tokens_are_stable_and_importable() -> None:
    assert CapabilityFamily.CORE.value == "core"
    assert CapabilityFamily.CHAT.value == "chat"
    assert CapabilityFamily.DOCUMENT.value == "document"
    assert CapabilityFamily.MEDIA.value == "media"
    assert CapabilityFamily.PROJECT.value == "project"
    assert CapabilityFamily.PERSONA_PROFILE.value == "persona_profile"
    assert CapabilityFamily.PLUGIN.value == "plugin"
    assert CapabilityFamily.RELEASE_FAMILY.value == "release_family"
    assert CapabilityFamily.QUOTA.value == "quota"
    assert CAPABILITY_FAMILIES == {
        "core",
        "chat",
        "document",
        "media",
        "project",
        "persona_profile",
        "plugin",
        "release_family",
        "quota",
    }
    assert CANONICAL_CAPABILITY_IDENTIFIERS == CAPABILITY_FAMILIES
