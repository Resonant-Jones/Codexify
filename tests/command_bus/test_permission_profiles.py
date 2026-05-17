from pathlib import Path

from guardian.command_bus.permission_profiles import (
    PermissionProfile,
    PermissionProfileRequest,
    evaluate_permission_profile,
)


def _profile(**overrides: object) -> PermissionProfile:
    payload: dict[str, object] = {
        "profile_id": "profile-1",
        "actor_id": "actor-1",
        "subject_id": "subject-1",
        "task_id": "task-1",
        "project_id": "project-1",
        "thread_id": "thread-1",
        "allowed_command_classes": (),
        "denied_command_classes": (),
        "allowed_command_ids": (),
        "denied_command_ids": (),
        "filesystem_access": "none",
        "allowed_write_roots": (),
        "shell_allowed": False,
        "shell_read_only": True,
        "allowed_shell_commands": (),
        "network_allowed": False,
        "connector_allowed": False,
    }
    payload.update(overrides)
    return PermissionProfile(**payload)


def _request(**overrides: object) -> PermissionProfileRequest:
    payload: dict[str, object] = {
        "actor_id": "actor-1",
        "subject_id": "subject-1",
        "task_id": "task-1",
        "command_id": "op::read.resource",
        "command_class": "read",
        "project_id": "project-1",
        "thread_id": "thread-1",
        "requested_write_paths": (),
        "uses_shell": False,
        "shell_command": None,
        "shell_mutates": False,
        "uses_network": False,
        "uses_connector": False,
    }
    payload.update(overrides)
    return PermissionProfileRequest(**payload)


def test_missing_profile_denies() -> None:
    decision = evaluate_permission_profile(None, _request())
    assert decision.allowed is False
    assert decision.code == "missing_profile"


def test_missing_actor_denies() -> None:
    decision = evaluate_permission_profile(_profile(), _request(actor_id=""))
    assert decision.allowed is False
    assert decision.code == "missing_actor"


def test_missing_subject_denies() -> None:
    decision = evaluate_permission_profile(_profile(), _request(subject_id=""))
    assert decision.allowed is False
    assert decision.code == "missing_subject"


def test_missing_task_denies() -> None:
    decision = evaluate_permission_profile(_profile(), _request(task_id=""))
    assert decision.allowed is False
    assert decision.code == "missing_task"


def test_missing_command_id_denies() -> None:
    decision = evaluate_permission_profile(_profile(), _request(command_id=""))
    assert decision.allowed is False
    assert decision.code == "missing_command_id"


def test_missing_command_class_denies() -> None:
    decision = evaluate_permission_profile(_profile(), _request(command_class=""))
    assert decision.allowed is False
    assert decision.code == "missing_command_class"


def test_actor_mismatch_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(actor_id="actor-2"),
        _request(actor_id="actor-1"),
    )
    assert decision.allowed is False
    assert decision.code == "actor_mismatch"


def test_subject_mismatch_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(subject_id="subject-2"),
        _request(subject_id="subject-1"),
    )
    assert decision.allowed is False
    assert decision.code == "subject_mismatch"


def test_task_mismatch_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(task_id="task-2"),
        _request(task_id="task-1"),
    )
    assert decision.allowed is False
    assert decision.code == "task_mismatch"


def test_project_scope_mismatch_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(project_id="project-a"),
        _request(project_id="project-b"),
    )
    assert decision.allowed is False
    assert decision.code == "project_scope_mismatch"


def test_thread_scope_mismatch_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(thread_id="thread-a"),
        _request(thread_id="thread-b"),
    )
    assert decision.allowed is False
    assert decision.code == "thread_scope_mismatch"


def test_matching_allowed_command_id_allows() -> None:
    decision = evaluate_permission_profile(
        _profile(allowed_command_ids=("op::read.resource",)),
        _request(command_id="op::read.resource"),
    )
    assert decision.allowed is True
    assert decision.code == "allowed"


def test_matching_allowed_command_class_allows() -> None:
    decision = evaluate_permission_profile(
        _profile(allowed_command_classes=("read",)),
        _request(command_class="read"),
    )
    assert decision.allowed is True
    assert decision.code == "allowed"


def test_denied_command_id_overrides_allowed_command_id() -> None:
    decision = evaluate_permission_profile(
        _profile(
            allowed_command_ids=("op::read.resource",),
            denied_command_ids=("op::read.resource",),
        ),
        _request(command_id="op::read.resource"),
    )
    assert decision.allowed is False
    assert decision.code == "command_id_denied"


def test_denied_command_class_overrides_allowed_command_class() -> None:
    decision = evaluate_permission_profile(
        _profile(
            allowed_command_classes=("write",),
            denied_command_classes=("write",),
        ),
        _request(command_class="write"),
    )
    assert decision.allowed is False
    assert decision.code == "command_class_denied"


def test_command_id_not_in_allowed_list_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(allowed_command_ids=("op::other.command",)),
        _request(command_id="op::read.resource"),
    )
    assert decision.allowed is False
    assert decision.code == "command_id_not_allowed"


def test_command_class_not_in_allowed_list_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(allowed_command_classes=("write",)),
        _request(command_class="read"),
    )
    assert decision.allowed is False
    assert decision.code == "command_class_not_allowed"


def test_write_path_inside_allowed_root_allows(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    decision = evaluate_permission_profile(
        _profile(
            filesystem_access="write_scoped",
            allowed_write_roots=(allowed_root,),
        ),
        _request(requested_write_paths=("nested/file.txt",)),
    )
    assert decision.allowed is True
    assert decision.code == "allowed"


def test_write_path_outside_allowed_root_denies(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    decision = evaluate_permission_profile(
        _profile(
            filesystem_access="write_scoped",
            allowed_write_roots=(allowed_root,),
        ),
        _request(requested_write_paths=("../escape.txt",)),
    )
    assert decision.allowed is False
    assert decision.code == "path_out_of_scope"


def test_write_path_symlink_escape_denies(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    (allowed_root / "escape").symlink_to(outside_root, target_is_directory=True)

    decision = evaluate_permission_profile(
        _profile(
            filesystem_access="write_scoped",
            allowed_write_roots=(allowed_root,),
        ),
        _request(requested_write_paths=("escape/payload.txt",)),
    )
    assert decision.allowed is False
    assert decision.code == "path_out_of_scope"


def test_write_request_denies_when_filesystem_access_none(
    tmp_path: Path,
) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    decision = evaluate_permission_profile(
        _profile(
            filesystem_access="none",
            allowed_write_roots=(allowed_root,),
        ),
        _request(requested_write_paths=("file.txt",)),
    )
    assert decision.allowed is False
    assert decision.code == "filesystem_denied"


def test_write_request_denies_when_allowed_write_roots_empty() -> None:
    decision = evaluate_permission_profile(
        _profile(filesystem_access="write_scoped", allowed_write_roots=()),
        _request(requested_write_paths=("file.txt",)),
    )
    assert decision.allowed is False
    assert decision.code == "filesystem_denied"


def test_shell_request_denies_unless_shell_allowed() -> None:
    decision = evaluate_permission_profile(
        _profile(shell_allowed=False),
        _request(uses_shell=True, shell_command="echo hi"),
    )
    assert decision.allowed is False
    assert decision.code == "shell_denied"


def test_shell_command_not_in_allowed_list_denies() -> None:
    decision = evaluate_permission_profile(
        _profile(shell_allowed=True, allowed_shell_commands=("echo hi",)),
        _request(uses_shell=True, shell_command="pwd"),
    )
    assert decision.allowed is False
    assert decision.code == "shell_command_not_allowed"


def test_shell_mutation_denies_when_shell_read_only_true() -> None:
    decision = evaluate_permission_profile(
        _profile(shell_allowed=True, shell_read_only=True),
        _request(
            uses_shell=True,
            shell_command="touch file.txt",
            shell_mutates=True,
        ),
    )
    assert decision.allowed is False
    assert decision.code == "shell_mutation_denied"


def test_network_request_denies_unless_network_allowed() -> None:
    decision = evaluate_permission_profile(
        _profile(network_allowed=False),
        _request(uses_network=True),
    )
    assert decision.allowed is False
    assert decision.code == "network_denied"


def test_connector_request_denies_unless_connector_allowed() -> None:
    decision = evaluate_permission_profile(
        _profile(connector_allowed=False),
        _request(uses_connector=True),
    )
    assert decision.allowed is False
    assert decision.code == "connector_denied"


def test_combined_allowed_request_allows(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    decision = evaluate_permission_profile(
        _profile(
            allowed_command_ids=("op::dispatch.execute",),
            filesystem_access="write_scoped",
            allowed_write_roots=(allowed_root,),
            shell_allowed=True,
            shell_read_only=False,
            allowed_shell_commands=("git status",),
            network_allowed=True,
            connector_allowed=True,
        ),
        _request(
            command_id="op::dispatch.execute",
            command_class="write",
            requested_write_paths=("safe/out.txt",),
            uses_shell=True,
            shell_command="git status",
            shell_mutates=True,
            uses_network=True,
            uses_connector=True,
        ),
    )
    assert decision.allowed is True
    assert decision.code == "allowed"
