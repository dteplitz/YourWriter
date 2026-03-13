"""Utilities for comparing two Identity snapshots.

Produces a list of human-readable descriptions of what changed between
an old and new identity, suitable for display in the evolution timeline.
"""

from __future__ import annotations

from typing import Any


def _list_diff(label: str, old: list[str], new: list[str]) -> list[str]:
    """Return change descriptions for a list field."""
    changes: list[str] = []
    old_set = set(old)
    new_set = set(new)

    for item in sorted(new_set - old_set):
        changes.append(f"Added {label}: \"{item}\"")

    for item in sorted(old_set - new_set):
        changes.append(f"Removed {label}: \"{item}\"")

    return changes


def _dict_diff(label: str, old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Return change descriptions for a dict field."""
    changes: list[str] = []
    all_keys = sorted(set(old) | set(new))

    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            if old_val is None:
                changes.append(f"Set {label} '{key}' to: {new_val}")
            elif new_val is None:
                changes.append(f"Cleared {label} '{key}' (was: {old_val})")
            else:
                changes.append(f"Changed {label} '{key}' from {old_val} to {new_val}")

    return changes


def compare_identities(
    old: dict[str, Any],
    new: dict[str, Any],
) -> list[str]:
    """Compare two identity dicts and return human-readable change descriptions.

    Parameters
    ----------
    old:
        The identity dict *before* evolution.
    new:
        The identity dict *after* evolution.

    Returns
    -------
    list[str]
        A list of plain-English descriptions of each change.  Returns an
        empty list when the identities are identical.
    """
    changes: list[str] = []

    # Scalar fields
    old_purpose = old.get("purpose", "general-purpose writing")
    new_purpose = new.get("purpose", "general-purpose writing")
    if old_purpose != new_purpose:
        changes.append(f"Changed purpose from \"{old_purpose}\" to \"{new_purpose}\"")

    list_fields = [
        ("personality", "personality trait"),
        ("emotions", "emotion"),
        ("memories", "memory"),
        ("topics", "topic"),
        ("lifelong_objectives", "lifelong objective"),
    ]

    for field_key, label in list_fields:
        changes.extend(
            _list_diff(label, old.get(field_key, []), new.get(field_key, []))
        )

    changes.extend(
        _dict_diff("constraint", old.get("constraints", {}), new.get("constraints", {}))
    )

    return changes
