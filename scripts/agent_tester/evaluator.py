"""Self-evaluation metrics and hypothesis data collection."""

from __future__ import annotations

from typing import Any


def _extract_scores(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract individual artifact scores from a session result."""
    scores = []
    for artifact_type, ev in result.get("evaluations", {}).items():
        scores.append({
            "artifact_type": artifact_type,
            "score": ev.get("score"),
            "useful": ev.get("useful"),
            "reasoning": ev.get("reasoning", ""),
        })
    return scores


def _find_by_condition(results: list[dict[str, Any]], persona: str, condition: str) -> dict[str, Any] | None:
    for r in results:
        if r["persona"] == persona and r["condition"] == condition:
            return r
    return None


def compute_h1_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare single-formalism (lean only) vs plural-formalism sessions."""
    personas_seen: set[str] = set()
    comparisons = []

    for r in results:
        if r["condition"] == "single_formalism":
            persona = r["persona"]
            if persona in personas_seen:
                continue
            plural = _find_by_condition(results, persona, "plural_formalism")
            if not plural:
                continue
            personas_seen.add(persona)

            comparisons.append({
                "persona": persona,
                "single_formalism": {
                    "condition": "single_formalism",
                    "scores": _extract_scores(r),
                    "satisfaction": r.get("finish_data", {}).get("satisfaction"),
                },
                "plural_formalism": {
                    "condition": "plural_formalism",
                    "scores": _extract_scores(plural),
                    "satisfaction": plural.get("finish_data", {}).get("satisfaction"),
                },
            })

    return {"comparisons": comparisons}


def compute_h2_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare single-shot vs iterative refinement sessions."""
    personas_seen: set[str] = set()
    comparisons = []

    for r in results:
        if r["condition"] == "single_shot":
            persona = r["persona"]
            if persona in personas_seen:
                continue
            iterative = _find_by_condition(results, persona, "iterative")
            if not iterative:
                continue
            personas_seen.add(persona)

            comparisons.append({
                "persona": persona,
                "single_shot": {
                    "condition": "single_shot",
                    "scores": _extract_scores(r),
                    "satisfaction": r.get("finish_data", {}).get("satisfaction"),
                },
                "iterative": {
                    "condition": "iterative",
                    "scores": _extract_scores(iterative),
                    "satisfaction": iterative.get("finish_data", {}).get("satisfaction"),
                },
            })

    return {"comparisons": comparisons}


def compute_h3_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare pure-LLM vs single-shot-app vs full-tool sessions."""
    personas_seen: set[str] = set()
    comparisons = []

    for r in results:
        if r["condition"] == "pure_llm":
            persona = r["persona"]
            if persona in personas_seen:
                continue
            single_shot = _find_by_condition(results, persona, "single_shot")
            full_tool = _find_by_condition(results, persona, "full_tool")
            if not full_tool:
                continue
            personas_seen.add(persona)

            entry: dict[str, Any] = {
                "persona": persona,
                "pure_llm": {
                    "condition": "pure_llm",
                    "scores": _extract_scores(r),
                    "satisfaction": r.get("finish_data", {}).get("satisfaction"),
                },
            }
            if single_shot:
                entry["single_shot"] = {
                    "condition": "single_shot",
                    "scores": _extract_scores(single_shot),
                    "satisfaction": single_shot.get("finish_data", {}).get("satisfaction"),
                }
            entry["full_tool"] = {
                "condition": "full_tool",
                "scores": _extract_scores(full_tool),
                "satisfaction": full_tool.get("finish_data", {}).get("satisfaction"),
            }
            comparisons.append(entry)

    return {"comparisons": comparisons}


def analyze_hypotheses(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute metrics for all three hypotheses."""
    return {
        "h1_pluralistic_vs_single": compute_h1_metrics(results),
        "h2_refinement_vs_single_shot": compute_h2_metrics(results),
        "h3_tool_vs_unaided": compute_h3_metrics(results),
    }
