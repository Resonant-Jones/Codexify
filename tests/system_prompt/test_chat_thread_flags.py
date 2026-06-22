from guardian.db.models import ChatThread


def test_chat_thread_defaults_diary_flags():
    for name in (
        "is_diary",
        "diary_mode",
        "exclude_from_identity",
        "modeling_excluded",
    ):
        column = ChatThread.__table__.c[name]
        assert column.default is not None
        assert column.default.arg is False
        assert column.server_default is not None
        assert str(column.server_default.arg) == "false"
