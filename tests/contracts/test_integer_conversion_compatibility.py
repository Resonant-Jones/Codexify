from array import array
from dataclasses import fields

import pytest

from guardian.agents.coding_agent_contracts import CodingExecutionBinding
from guardian.watchdog.contracts import normalize_github_delivery


class OneViaInt:
    def __int__(self):
        return 1


class OneViaIndex:
    def __index__(self):
        return 1


def binding_with(field, value):
    payload = {item.name: "fixture" for item in fields(CodingExecutionBinding)}
    payload.update(harness_selection_mode="default", schema_version=1, max_attempts=1)
    payload[field] = value
    return CodingExecutionBinding.from_dict(payload)


def watchdog_number(value):
    delivery = normalize_github_delivery(
        github_delivery_id="fixture",
        event_name="pull_request",
        payload={"action": "opened", "number": value},
        payload_sha256="fixture",
    )
    return delivery.pull_request_number


@pytest.mark.parametrize("field", ["schema_version", "max_attempts"])
@pytest.mark.parametrize(
    "value", [1, True, "1", 1.75, array("B", b"1"), OneViaInt(), OneViaIndex()]
)
def test_binding_accepts_native_integer_inputs(field, value):
    assert getattr(binding_with(field, value), field) == 1


@pytest.mark.parametrize("field", ["schema_version", "max_attempts"])
@pytest.mark.parametrize("value", [{"bad": 1}, "invalid", float("inf")])
def test_binding_preserves_conversion_errors(field, value):
    with pytest.raises((TypeError, ValueError, OverflowError)) as original:
        int(value)
    with pytest.raises(type(original.value)) as actual:
        binding_with(field, value)
    assert actual.value.args == original.value.args


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (array("B", b"2"), 2),
        (OneViaInt(), 1),
        (OneViaIndex(), 1),
        ("3", 3),
        (True, None),
        (None, None),
        (0, None),
        (-1, None),
        ({"bad": 1}, None),
        ("invalid", None),
    ],
)
def test_watchdog_preserves_number_or_absence(value, expected):
    assert watchdog_number(value) == expected


def test_watchdog_propagates_overflow():
    with pytest.raises(OverflowError) as original:
        int(float("inf"))
    with pytest.raises(OverflowError) as actual:
        watchdog_number(float("inf"))
    assert actual.value.args == original.value.args
