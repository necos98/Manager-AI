"""Strict parser for startup-command conditions.

Supported grammar:

    $<var> (== | !=) <value>

where `<var>` is an identifier and `<value>` is any non-empty literal
(optional matching quotes stripped). Anything else raises
:class:`UnknownConditionError` — the router logs and skips the command
instead of silently executing it.
"""
from __future__ import annotations

import re

_CONDITION_RE = re.compile(
    r"^\s*\$(?P<var>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<op>==|!=)\s*(?P<value>.+?)\s*$"
)


class UnknownConditionError(ValueError):
    """Raised when a condition string doesn't match the supported grammar."""


def evaluate_condition(condition: str | None, variables: dict[str, str]) -> bool:
    """Evaluate ``condition`` against ``variables``.

    Empty/absent conditions evaluate to True (the command runs). A
    reference to an unknown variable evaluates to False (the command is
    skipped). Syntactically invalid conditions raise
    :class:`UnknownConditionError`.
    """
    if not condition or not condition.strip():
        return True
    match = _CONDITION_RE.match(condition)
    if not match:
        raise UnknownConditionError(f"Unparseable condition: {condition!r}")
    var = match.group("var")
    op = match.group("op")
    expected = match.group("value").strip()
    # Strip matched surrounding quotes.
    if len(expected) >= 2 and expected[0] == expected[-1] and expected[0] in ("'", '"'):
        expected = expected[1:-1]
    actual = variables.get(var)
    if actual is None:
        return False
    if op == "==":
        return actual == expected
    return actual != expected
