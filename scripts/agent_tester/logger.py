"""JSONL session logging and hypothesis results summary."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .experiment import SessionSpec


class SessionLogger:
    """Writes one JSONL line per agent step, plus a final summary."""

    def __init__(self, output_dir: str, spec: SessionSpec) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"session_{spec.session_id:03d}_{spec.persona.name}_{spec.condition}.jsonl"
        self._path = self._output_dir / filename
        self._step_count = 0
        # Truncate file on creation
        self._path.write_text("")

    @property
    def path(self) -> Path:
        return self._path

    def log_step(
        self,
        iteration: int,
        action: str,
        params: dict[str, Any],
        *,
        api_endpoint: str | None = None,
        api_status: int | None = None,
        api_response_summary: str | None = None,
        duration_ms: int = 0,
        reasoning: str = "",
    ) -> None:
        self._step_count += 1
        entry = {
            "step": self._step_count,
            "iteration": iteration,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "params": _sanitize_params(params),
        }
        if api_endpoint:
            entry["api_endpoint"] = api_endpoint
        if api_status is not None:
            entry["api_status"] = api_status
        if api_response_summary:
            entry["api_response_summary"] = api_response_summary
        if duration_ms:
            entry["duration_ms"] = duration_ms
        if reasoning:
            entry["agent_reasoning"] = reasoning

        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def write_hypothesis_results(output_dir: str, analysis: dict[str, Any]) -> Path:
    """Write the aggregate hypothesis results JSON."""
    path = Path(output_dir) / "hypothesis_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(analysis, f, indent=2)
    return path


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Truncate long string values in params for logging."""
    sanitized = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 500:
            sanitized[k] = v[:500] + "..."
        else:
            sanitized[k] = v
    return sanitized
