"""Orchestrator: runs all experiment sessions and produces final analysis."""

from __future__ import annotations

import os
import time
from typing import Any

from .agent import run_agent_loop
from .api_client import AppClient
from .config import AgentConfig
from .evaluator import analyze_hypotheses
from .experiment import SessionSpec, build_experiment_plan
from .logger import SessionLogger, write_hypothesis_results
from .session_state import SessionState


def run_session(
    spec: SessionSpec,
    client: AppClient,
    config: AgentConfig,
) -> dict[str, Any]:
    """Run a single agent session for one experiment condition."""
    logger = SessionLogger(config.output_dir, spec)

    state = SessionState(
        persona=spec.persona,
        condition=spec.condition,
    )

    # If we have shared source material from a paired session, pre-fill it
    if spec.shared_source:
        state.source_text = spec.shared_source.get("source_text", "")
        state.context = spec.shared_source.get("context", "")
        if state.source_text:
            state.phase = "input_ready"

    if config.verbose:
        print(f"\n{'='*60}")
        print(f"Session {spec.session_id}: {spec.persona.name} | {','.join(spec.hypotheses)} | {spec.condition}")
        print(f"{'='*60}")

    result = run_agent_loop(state, client, config, logger)

    if config.verbose:
        print(f"\nSession {spec.session_id} complete: {result.get('iterations', 0)} iterations")
        for atype, ev in result.get("evaluations", {}).items():
            print(f"  {atype}: score={ev.get('score')}/5, useful={ev.get('useful')}")

    return result


def _print_scores(label: str, data: dict[str, Any]) -> None:
    """Print individual artifact scores for a condition."""
    scores = data.get("scores", [])
    satisfaction = data.get("satisfaction")
    if not scores:
        print(f"    {label}: (no scores)")
        return
    for s in scores:
        useful_str = "useful" if s.get("useful") else "not useful"
        print(f"    {label} | {s['artifact_type']}: {s.get('score')}/5 ({useful_str})")
    if satisfaction is not None:
        print(f"    {label} | overall satisfaction: {satisfaction}/5")


def _print_analysis(analysis: dict[str, Any]) -> None:
    """Print human-readable summary with individual scores."""
    for hyp_key, hyp_data in analysis.items():
        print(f"\n  {hyp_key}:")
        for comp in hyp_data.get("comparisons", []):
            print(f"    --- {comp['persona']} ---")
            for key, val in comp.items():
                if key == "persona":
                    continue
                if isinstance(val, dict) and "scores" in val:
                    _print_scores(val["condition"], val)


def run_all(config: AgentConfig) -> None:
    """Run the full experiment plan and produce analysis."""
    plan = build_experiment_plan(config)

    # Create timestamped run directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    config.output_dir = os.path.join(config.output_dir, f"run_{timestamp}")

    if not plan:
        print("No sessions to run. Check your --hypothesis and --persona settings.")
        return

    print(f"Experiment plan: {len(plan)} sessions")
    for spec in plan:
        print(f"  #{spec.session_id}: {spec.persona.name} | {','.join(spec.hypotheses)} | {spec.condition} (group: {spec.pair_group})")
    print()

    client = AppClient(config.base_url)
    results: list[dict[str, Any]] = []

    # Track shared source material by pair group (= persona name)
    shared_sources: dict[str, dict[str, str]] = {}

    try:
        for spec in plan:
            # If a paired session already ran, share the source material
            if spec.pair_group in shared_sources and spec.shared_source is None:
                spec.shared_source = shared_sources[spec.pair_group]

            result = run_session(spec, client, config)
            results.append(result)

            # Store source material for paired sessions
            if spec.pair_group not in shared_sources and result.get("source_text"):
                shared_sources[spec.pair_group] = {
                    "source_text": result["source_text"],
                    "context": result.get("context", ""),
                }

    finally:
        client.close()

    # Analyze hypotheses
    print("\nAnalyzing hypothesis results...")
    analysis = analyze_hypotheses(results)
    results_path = write_hypothesis_results(config.output_dir, analysis)

    print(f"\nResults written to {results_path}")
    _print_analysis(analysis)
    print(f"\nSession logs in {config.output_dir}/")
