"""Mutable session state tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .personas import Persona

# Maps artifact type to the JSON key the API returns its content under
ARTIFACT_RESPONSE_KEYS: dict[str, str] = {
    "semiformal": "proof",
    "lean": "leanCode",
    "causal-graph": "causalGraph",
    "statistical-model": "statisticalModel",
    "property-tests": "propertyTests",
    "dialectical-map": "dialecticalMap",
}


@dataclass
class SessionState:
    persona: Persona
    condition: str  # single_formalism | plural_formalism | single_shot | iterative | pure_llm | full_tool
    phase: str = "init"  # init | input_ready | context_refined | decomposed | artifacts_ready | editing | evaluating | done
    source_text: str = ""
    context: str = ""
    propositions: list[dict[str, Any]] | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)  # artifact_type -> response content
    artifact_evaluations: dict[str, dict[str, Any]] = field(default_factory=dict)
    lean_code: str = ""
    lean_verified: bool = False
    iteration_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.history, dict):
            self.history = []

    def summary_for_agent(self) -> str:
        """Serialize current state into structured text for the LLM context."""
        parts: list[str] = []

        parts.append(f"[Session State]")
        parts.append(f"Condition: {self.condition}")
        parts.append(f"Phase: {self.phase}")
        parts.append(f"Iteration: {self.iteration_count}")
        parts.append("")

        if self.source_text:
            preview = self.source_text[:500] + ("..." if len(self.source_text) > 500 else "")
            parts.append(f"[Source Text]\n{preview}")
            parts.append("")

        if self.context:
            parts.append(f"[Context]\n{self.context}")
            parts.append("")

        if self.propositions:
            parts.append(f"[Decomposition] {len(self.propositions)} nodes extracted:")
            for p in self.propositions[:10]:
                parts.append(f"  - {p.get('id', '?')}: {p.get('label', '?')} ({p.get('kind', '?')})")
            if len(self.propositions) > 10:
                parts.append(f"  ... and {len(self.propositions) - 10} more")
            parts.append("")

        if self.artifacts:
            parts.append("[Generated Artifacts]")
            for atype, content in self.artifacts.items():
                if isinstance(content, str):
                    preview = content[:300] + ("..." if len(content) > 300 else "")
                else:
                    import json
                    s = json.dumps(content, indent=2)
                    preview = s[:300] + ("..." if len(s) > 300 else "")
                parts.append(f"  [{atype}]\n{preview}")
            parts.append("")

        if self.lean_code:
            parts.append(f"[Lean Code] (verified={self.lean_verified})")
            preview = self.lean_code[:300] + ("..." if len(self.lean_code) > 300 else "")
            parts.append(preview)
            parts.append("")

        if self.artifact_evaluations:
            parts.append("[Evaluations So Far]")
            for atype, ev in self.artifact_evaluations.items():
                parts.append(f"  {atype}: score={ev.get('score')}/5, useful={ev.get('useful')}")
            parts.append("")

        if self.history:
            parts.append(f"[Action History] ({len(self.history)} steps)")
            for h in self.history[-5:]:
                parts.append(f"  Step {h.get('step', '?')}: {h.get('action', '?')}")
            parts.append("")

        return "\n".join(parts)
