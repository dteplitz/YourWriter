"""Constraint validation tools for writer agents.

Validates that generated content satisfies the structured constraints
(word count, audience alignment, etc.) and returns a report of any
violations.
"""

from __future__ import annotations

from typing import Any


def _count_words(text: str) -> int:
    """Count words in *text* using whitespace splitting."""
    return len(text.split())


def validate_constraints(
    content: str,
    constraints: dict[str, Any],
) -> dict[str, Any]:
    """Validate *content* against the given *constraints* dict.

    Parameters
    ----------
    content:
        The generated text to validate.
    constraints:
        A dict that may contain: word_limit (int|None), audience (str|None),
        genre (str|None), tone (str|None), custom_rules (list[str]).

    Returns
    -------
    dict with keys:
        - valid (bool): True if all checkable constraints pass.
        - word_count (int): actual word count of the content.
        - violations (list[str]): human-readable descriptions of failures.
        - warnings (list[str]): non-blocking notes.
    """
    violations: list[str] = []
    warnings: list[str] = []
    word_count = _count_words(content)

    # -- Word limit ----------------------------------------------------------
    word_limit = constraints.get("word_limit")
    if word_limit is not None:
        try:
            limit = int(word_limit)
            if word_count > limit:
                violations.append(
                    f"Word count ({word_count}) exceeds limit ({limit})."
                )
            elif word_count < limit * 0.5:
                warnings.append(
                    f"Word count ({word_count}) is well under the limit "
                    f"({limit}).  The content may feel thin."
                )
        except (TypeError, ValueError):
            warnings.append(
                f"Could not interpret word_limit value: {word_limit!r}"
            )

    # -- Audience / genre / tone ---------------------------------------------
    # These require semantic analysis that we cannot do with simple string
    # checks.  For now we surface them as reminders so the refine node can
    # address them via the LLM.
    audience = constraints.get("audience")
    if audience and audience != "general":
        warnings.append(f"Target audience: {audience} — verify appropriateness.")

    genre = constraints.get("genre")
    if genre:
        warnings.append(f"Genre: {genre} — verify genre alignment.")

    tone = constraints.get("tone")
    if tone:
        warnings.append(f"Tone: {tone} — verify tone consistency.")

    # -- Custom rules --------------------------------------------------------
    custom_rules = constraints.get("custom_rules", [])
    if custom_rules:
        rules_text = "; ".join(custom_rules)
        warnings.append(f"Custom rules to verify: {rules_text}")

    return {
        "valid": len(violations) == 0,
        "word_count": word_count,
        "violations": violations,
        "warnings": warnings,
    }


def format_constraints_for_prompt(constraints: dict[str, Any]) -> str:
    """Format a constraints dict as a human-readable string for prompts.

    Parameters
    ----------
    constraints:
        The structured constraints dict.

    Returns
    -------
    str
        Formatted multi-line string.
    """
    lines: list[str] = []

    word_limit = constraints.get("word_limit")
    if word_limit is not None:
        lines.append(f"- Word limit: {word_limit} words maximum")

    audience = constraints.get("audience")
    if audience:
        lines.append(f"- Target audience: {audience}")

    genre = constraints.get("genre")
    if genre:
        lines.append(f"- Genre/style: {genre}")

    tone = constraints.get("tone")
    if tone:
        lines.append(f"- Tone: {tone}")

    custom_rules = constraints.get("custom_rules", [])
    for rule in custom_rules:
        lines.append(f"- {rule}")

    return "\n".join(lines) if lines else "No specific constraints set."
