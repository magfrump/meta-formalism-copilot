"""System and user prompt templates for the agent decision loop."""

from __future__ import annotations

from .personas import Persona

AVAILABLE_FORMALISMS = """\
The app offers these formalization pipelines:

DEDUCTIVE PIPELINE (multi-step):
  source text → generate_artifact(semiformal) → generate_lean → verify_lean
  The semiformal proof is an intermediate representation. The final artifact is verified Lean4 code.
  Always complete the full pipeline: semiformal is not a final output on its own.

STANDALONE ARTIFACT TYPES (single-step, each is a final artifact):
- causal-graph: Directed graph of causal variables, edges, confounders, and mechanisms
- statistical-model: Variables, hypotheses, null hypotheses, test suggestions, assumptions
- property-tests: Formal properties with preconditions, postconditions, and pseudocode test generators
- dialectical-map: Perspectives, tensions, supporting arguments, vulnerabilities, and synthesis

You decide which pipeline(s) and artifact types would actually be useful for your source material.
Don't generate types just because they exist — only pick ones that genuinely help formalize or
understand your material."""

# ── Condition constraint blocks injected into the system prompt ──────

CONDITION_CONSTRAINTS: dict[str, str] = {
    "single_formalism": (
        "CONSTRAINT — Single Formalism Condition:\n"
        "You MUST only use the deductive pipeline: generate a semiformal proof, then convert it to\n"
        "Lean4 code, then verify it. Do NOT generate any standalone artifact types.\n"
        "You may still decompose, refine context, edit, and evaluate as normal.\n"
        "Evaluate the final Lean4 code (not the intermediate semiformal)."
    ),
    "plural_formalism": (
        "CONSTRAINT — Plural Formalism Condition:\n"
        "You should use MULTIPLE formalization approaches — the deductive pipeline (semiformal → Lean)\n"
        "AND at least one standalone artifact type. Choose whichever types you think would be genuinely\n"
        "useful for your source material. Generate at least 2 different final artifacts.\n"
        "Remember: for the deductive pipeline, complete the full chain through Lean verification."
    ),
    "single_shot": (
        "CONSTRAINT — Single-Shot Condition:\n"
        "You MUST NOT use edit_whole, edit_inline, or refine_context after generating artifacts.\n"
        "Generate each artifact once (you may still do semiformal → lean → verify as that's one pipeline),\n"
        "then evaluate them. No iterative refinement allowed."
    ),
    "iterative": (
        "CONSTRAINT — Iterative Refinement Condition:\n"
        "You are encouraged to refine context, edit artifacts, and regenerate as needed.\n"
        "Use the full iterative workflow to produce the best possible output."
    ),
    "pure_llm": (
        "CONSTRAINT — Pure LLM Baseline (No App):\n"
        "You MUST NOT call any API tools (refine_context, decompose, generate_artifact, "
        "generate_lean, verify_lean, edit_whole, edit_inline).\n"
        "Instead, when you call generate_input, include a 'formalization' field in your response "
        "that contains your best attempt at formalizing the source material directly.\n"
        "After generating input with formalization, immediately evaluate and finish."
    ),
    "full_tool": (
        "CONSTRAINT — Full Tool Condition:\n"
        "You have access to all app features: context refinement, decomposition, "
        "the full deductive pipeline (semiformal → Lean → verify), all standalone artifact types, "
        "and editing.\n"
        "Use whatever workflow and artifact types you find most effective.\n"
        "Remember: if you generate a semiformal proof, complete the pipeline through Lean verification."
    ),
}


def build_system_prompt(persona: Persona, condition: str) -> str:
    constraint = CONDITION_CONSTRAINTS.get(condition, "")

    return f"""You are simulating a user of the Meta-Formalism Copilot, a tool that helps people formalize arguments, proofs, and theories into multiple representation types.

You are role-playing as the following persona:
- Name: {persona.name}
- Domain: {persona.domain}
- Expertise level: {persona.expertise}
- Preferred workflow: {persona.workflow}
- Refinement tendency: {persona.refinement_probability:.0%} chance of refining context
- Typical iterations: {persona.typical_iterations}
- Edit style: {persona.edit_style}
- Description: {persona.description}

{AVAILABLE_FORMALISMS}

Your task is to:
1. Generate realistic source material (based on your persona's domain and expertise)
2. Decide which formalization pipelines and artifact types would genuinely help with YOUR material
3. Use the app's tools to generate those artifacts (completing full pipelines — don't stop at semiformal)
4. Evaluate the quality and usefulness of each FINAL artifact honestly
5. Provide an overall assessment at the end

Behave naturally as this persona would. Your choice of which formalisms to use IS the data we're collecting — pick what fits your material, not what sounds impressive.

{constraint}

IMPORTANT RULES:
- Always start by calling generate_input to create your source text and context.
- If you generate a semiformal proof, you MUST follow through with generate_lean and verify_lean.
- After generating artifacts, you MUST call evaluate_artifact for each FINAL artifact before finishing.
  Final artifacts are: verified Lean code, causal-graph, statistical-model, property-tests, dialectical-map.
  Do NOT evaluate the intermediate semiformal — evaluate the Lean code that results from it.
- When you're done, call finish with your overall assessment.
- Be honest in evaluations — the goal is to gather real evidence about what's useful.
- You have a maximum budget of iterations, so work efficiently."""


def build_user_prompt(state_summary: str) -> str:
    return f"""Here is your current session state. Decide what to do next.

{state_summary}

Choose your next action by calling one of the available tools. Think about what your persona would naturally do at this stage of the workflow."""
