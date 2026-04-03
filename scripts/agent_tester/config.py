"""Configuration and CLI argument parsing."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    base_url: str = "http://localhost:3000"
    openrouter_api_key: str = ""
    agent_model: str = "anthropic/claude-sonnet-4-6"
    num_sessions: int = 8
    max_iterations: int = 15
    persona: str | None = None
    output_dir: str = "./agent_test_results"
    hypothesis: str | None = None  # "h1", "h2", "h3", or None for all
    verbose: bool = False


def parse_args(argv: list[str] | None = None) -> AgentConfig:
    parser = argparse.ArgumentParser(
        prog="agent_tester",
        description="Simulate user testing of Meta-Formalism Copilot with LLM agent personas.",
    )
    parser.add_argument("--base-url", default="http://localhost:3000", help="App base URL")
    parser.add_argument("--model", default="anthropic/claude-sonnet-4-6", help="OpenRouter model ID for the agent")
    parser.add_argument("--sessions", type=int, default=8, help="Number of sessions")
    parser.add_argument("--max-iterations", type=int, default=15, help="Max steps per session")
    parser.add_argument("--persona", default=None, help="Specific persona name, or rotate through all")
    parser.add_argument("--hypothesis", default=None, choices=["h1", "h2", "h3", "all"], help="Run specific hypothesis or all")
    parser.add_argument("--output-dir", default="./agent_test_results", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Print step-by-step output")

    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        parser.error("OPENROUTER_API_KEY environment variable is required")

    hypothesis = args.hypothesis
    if hypothesis == "all":
        hypothesis = None

    return AgentConfig(
        base_url=args.base_url,
        openrouter_api_key=api_key,
        agent_model=args.model,
        num_sessions=args.sessions,
        max_iterations=args.max_iterations,
        persona=args.persona,
        output_dir=args.output_dir,
        hypothesis=hypothesis,
        verbose=args.verbose,
    )
