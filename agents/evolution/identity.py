"""Identity dataclass for AI writers.

Defines the evolving identity of a writer agent, including personality,
emotions, memories, topics, constraints, and lifelong objectives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Identity:
    """Represents the evolving identity of a writer agent.

    Each writer has a unique identity that shapes its voice, style, and
    behavior. The identity evolves over time through writing sessions
    and user feedback.
    """

    purpose: str = field(default="general-purpose writing")
    personality: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    lifelong_objectives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the identity to a plain dictionary."""
        return {
            "purpose": self.purpose,
            "personality": list(self.personality),
            "emotions": list(self.emotions),
            "memories": list(self.memories),
            "topics": list(self.topics),
            "constraints": dict(self.constraints),
            "lifelong_objectives": list(self.lifelong_objectives),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Identity:
        """Reconstruct an Identity from a dictionary.

        Unknown keys are silently ignored so that forward-compatible
        data can be loaded without errors.
        """
        return cls(
            purpose=data.get("purpose", "general-purpose writing"),
            personality=list(data.get("personality", [])),
            emotions=list(data.get("emotions", [])),
            memories=list(data.get("memories", [])),
            topics=list(data.get("topics", [])),
            constraints=dict(data.get("constraints", {})),
            lifelong_objectives=list(data.get("lifelong_objectives", [])),
        )

    def to_prompt_string(self) -> str:
        """Format the identity as a human-readable string for use in prompts."""
        sections: list[str] = []

        if self.purpose:
            sections.append(f"Purpose: {self.purpose}")

        if self.personality:
            traits = ", ".join(self.personality)
            sections.append(f"Personality: {traits}")

        if self.emotions:
            emotions = ", ".join(self.emotions)
            sections.append(f"Current emotions: {emotions}")

        if self.memories:
            mem_lines = "\n".join(f"  - {m}" for m in self.memories)
            sections.append(f"Memories:\n{mem_lines}")

        if self.topics:
            topics = ", ".join(self.topics)
            sections.append(f"Areas of interest/expertise: {topics}")

        if self.constraints:
            constraint_lines = "\n".join(
                f"  - {k}: {v}" for k, v in self.constraints.items()
            )
            sections.append(f"Constraints:\n{constraint_lines}")

        if self.lifelong_objectives:
            obj_lines = "\n".join(f"  - {o}" for o in self.lifelong_objectives)
            sections.append(f"Lifelong objectives:\n{obj_lines}")

        return "\n\n".join(sections)
