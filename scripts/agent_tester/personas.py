"""Built-in user personas for agent testing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    name: str
    domain: str
    expertise: str  # "expert" | "intermediate" | "novice"
    workflow: str  # "decompose_first" | "direct_formalize"
    refinement_probability: float  # 0.0-1.0 — how likely to refine context
    typical_iterations: int
    edit_style: str  # "precision" | "expansion" | "restructure"
    source_material_hint: str
    description: str


PERSONAS: dict[str, Persona] = {
    "dr_chen": Persona(
        name="dr_chen",
        domain="mathematics",
        expertise="expert",
        workflow="decompose_first",
        refinement_probability=0.1,
        typical_iterations=4,
        edit_style="precision",
        source_material_hint="a half-formed proof about compact topological spaces and continuous functions",
        description=(
            "Dr. Chen is a mathematics professor who works with formal proofs. "
            "She prefers precise, minimal outputs and decomposes problems before formalizing. "
            "She rarely refines context because she writes precise input from the start."
        ),
    ),
    "maya_grad": Persona(
        name="maya_grad",
        domain="philosophy",
        expertise="intermediate",
        workflow="direct_formalize",
        refinement_probability=0.6,
        typical_iterations=3,
        edit_style="expansion",
        source_material_hint="an argument about the relationship between consciousness and information integration theory",
        description=(
            "Maya is a philosophy graduate student exploring formal methods for argumentation. "
            "She often refines her context because her initial descriptions are exploratory."
        ),
    ),
    "prof_nielsen": Persona(
        name="prof_nielsen",
        domain="empirical_science",
        expertise="expert",
        workflow="decompose_first",
        refinement_probability=0.3,
        typical_iterations=2,
        edit_style="precision",
        source_material_hint="a research hypothesis about the causal relationship between sleep quality, cortisol levels, and cognitive performance",
        description=(
            "Prof. Nielsen is an empirical researcher who uses the tool to formalize causal hypotheses. "
            "He decomposes research questions into component claims. "
            "He makes targeted edits for precision."
        ),
    ),
    "alex_novice": Persona(
        name="alex_novice",
        domain="interdisciplinary",
        expertise="novice",
        workflow="direct_formalize",
        refinement_probability=0.8,
        typical_iterations=5,
        edit_style="restructure",
        source_material_hint="a vague idea about how social media algorithms amplify political polarization",
        description=(
            "Alex is an undergraduate exploring formalization for the first time. "
            "They frequently refine context and often restructure their approach mid-session. "
            "Their input is informal and exploratory."
        ),
    ),
    "sam_systems": Persona(
        name="sam_systems",
        domain="CS/math",
        expertise="intermediate",
        workflow="decompose_first",
        refinement_probability=0.4,
        typical_iterations=3,
        edit_style="precision",
        source_material_hint="a specification for a distributed consensus algorithm with liveness and safety properties",
        description=(
            "Sam is a systems engineer who uses formalization to verify software specifications. "
            "They decompose specs into properties and make precise edits to tighten specifications."
        ),
    ),
}


def get_persona(name: str) -> Persona:
    if name not in PERSONAS:
        raise ValueError(f"Unknown persona: {name!r}. Available: {list(PERSONAS.keys())}")
    return PERSONAS[name]


def all_persona_names() -> list[str]:
    return list(PERSONAS.keys())
