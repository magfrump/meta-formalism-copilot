"""Synchronous HTTP client wrapping all Meta-Formalism Copilot API endpoints."""

from __future__ import annotations

import time
from typing import Any

import requests


class AppClient:
    """Thin wrapper around the app's HTTP API using requests."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()

    def _post(
        self, path: str, body: dict[str, Any], timeout: float = 120.0,
    ) -> tuple[int, dict[str, Any]]:
        t0 = time.monotonic()
        try:
            r = self._session.post(
                f"{self._base_url}{path}", json=body, timeout=timeout,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            return r.status_code, {**data, "_elapsed_ms": elapsed_ms}
        except requests.Timeout:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return 504, {"error": "Request timed out", "_elapsed_ms": elapsed_ms}
        except requests.RequestException as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return 502, {"error": str(exc), "_elapsed_ms": elapsed_ms}

    # ── Context refinement ─────────────────────────────────────────────
    def refine_context(self, text: str, action: str) -> tuple[int, dict[str, Any]]:
        """POST /api/refine/context  body: {text, action}"""
        return self._post("/api/refine/context", {"text": text, "action": action})

    # ── Decomposition ──────────────────────────────────────────────────
    def decompose(self, documents: list[dict[str, str]]) -> tuple[int, dict[str, Any]]:
        """POST /api/decomposition/extract  body: {documents: [{sourceId, sourceLabel, text}]}"""
        return self._post("/api/decomposition/extract", {"documents": documents})

    # ── Artifact generation (generic) ──────────────────────────────────
    def generate_artifact(
        self,
        artifact_type: str,
        source_text: str,
        context: str,
        node_id: str | None = None,
        node_label: str | None = None,
        previous_attempt: str | None = None,
        instruction: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """POST /api/formalization/{type}  (semiformal, causal-graph, etc.)"""
        body: dict[str, Any] = {"sourceText": source_text, "context": context}
        if node_id:
            body["nodeId"] = node_id
        if node_label:
            body["nodeLabel"] = node_label
        if previous_attempt:
            body["previousAttempt"] = previous_attempt
        if instruction:
            body["instruction"] = instruction
        return self._post(f"/api/formalization/{artifact_type}", body)

    # ── Lean generation ────────────────────────────────────────────────
    def generate_lean(
        self,
        informal_proof: str,
        previous_attempt: str | None = None,
        errors: str | None = None,
        instruction: str | None = None,
        context_lean_code: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """POST /api/formalization/lean"""
        body: dict[str, Any] = {"informalProof": informal_proof}
        if previous_attempt:
            body["previousAttempt"] = previous_attempt
        if errors:
            body["errors"] = errors
        if instruction:
            body["instruction"] = instruction
        if context_lean_code:
            body["contextLeanCode"] = context_lean_code
        return self._post("/api/formalization/lean", body)

    # ── Lean verification ──────────────────────────────────────────────
    def verify_lean(self, lean_code: str) -> tuple[int, dict[str, Any]]:
        """POST /api/verification/lean"""
        return self._post("/api/verification/lean", {"leanCode": lean_code}, timeout=180.0)

    # ── Editing ────────────────────────────────────────────────────────
    def edit_inline(
        self,
        full_text: str,
        selection_start: int,
        selection_end: int,
        selection_text: str,
        instruction: str,
    ) -> tuple[int, dict[str, Any]]:
        """POST /api/edit/inline"""
        return self._post("/api/edit/inline", {
            "fullText": full_text,
            "selection": {"start": selection_start, "end": selection_end, "text": selection_text},
            "instruction": instruction,
        })

    def edit_whole(self, full_text: str, instruction: str) -> tuple[int, dict[str, Any]]:
        """POST /api/edit/whole"""
        return self._post("/api/edit/whole", {"fullText": full_text, "instruction": instruction})
