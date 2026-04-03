"""Experiment plan builder — generates all conditions per persona for hypothesis testing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import AgentConfig
from .personas import PERSONAS, Persona, get_persona

# All 7 conditions, grouped by which hypothesis they serve
H1_CONDITIONS = ["single_formalism", "plural_formalism"]
H2_CONDITIONS = ["single_shot", "iterative"]
H3_CONDITIONS = ["pure_llm", "single_shot", "full_tool"]

# Map condition -> which hypotheses it contributes data to
CONDITION_HYPOTHESES: dict[str, list[str]] = {
    "single_formalism": ["h1"],
    "plural_formalism": ["h1"],
    "single_shot": ["h2", "h3"],   # shared across H2 and H3
    "iterative": ["h2"],
    "pure_llm": ["h3"],
    "full_tool": ["h3"],
}

# Deduplicated ordered list of all conditions
ALL_CONDITIONS = ["single_formalism", "plural_formalism", "single_shot", "iterative", "pure_llm", "full_tool"]


@dataclass
class SessionSpec:
    """Specification for a single test session."""
    session_id: int
    persona: Persona
    condition: str
    hypotheses: list[str]   # which hypotheses this session contributes to
    pair_group: str          # persona name — all sessions for same persona share source material
    shared_source: dict[str, str] | None = None


def build_experiment_plan(config: AgentConfig) -> list[SessionSpec]:
    """Generate sessions: all relevant conditions per persona, sharing source material."""

    # Select personas
    if config.persona:
        persona_names = [config.persona]
    else:
        persona_names = list(PERSONAS.keys())

    # Determine which conditions to run based on hypothesis filter
    if config.hypothesis:
        hyp = config.hypothesis
        if hyp == "h1":
            conditions = H1_CONDITIONS
        elif hyp == "h2":
            conditions = H2_CONDITIONS
        elif hyp == "h3":
            conditions = H3_CONDITIONS
        else:
            conditions = ALL_CONDITIONS
    else:
        conditions = ALL_CONDITIONS

    specs: list[SessionSpec] = []
    session_counter = 0

    for pname in persona_names:
        persona = get_persona(pname)
        for cond in conditions:
            session_counter += 1
            hyps = CONDITION_HYPOTHESES[cond]
            # Filter to only requested hypotheses
            if config.hypothesis:
                hyps = [h for h in hyps if h == config.hypothesis]
            specs.append(SessionSpec(
                session_id=session_counter,
                persona=persona,
                condition=cond,
                hypotheses=hyps,
                pair_group=pname,  # all conditions for same persona share source
            ))

    # Trim to budget — keep complete persona groups
    if len(specs) > config.num_sessions:
        conds_per_persona = len(conditions)
        max_personas = max(1, config.num_sessions // conds_per_persona)
        specs = specs[:max_personas * conds_per_persona]

    return specs
