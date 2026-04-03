"""Core agent decision loop using OpenRouter via requests (OpenAI-compatible tool_use)."""

from __future__ import annotations

import json
from typing import Any

import requests

from .api_client import AppClient
from .config import AgentConfig
from .logger import SessionLogger
from .personas import Persona
from .prompts import build_system_prompt, build_user_prompt
from .session_state import ARTIFACT_RESPONSE_KEYS, SessionState

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Tool definitions in OpenAI function-calling format ──────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "generate_input",
            "description": (
                "Generate the source text and context for this session. "
                "This must be your first action. Create realistic material matching your persona."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source_text": {
                        "type": "string",
                        "description": "The source material to formalize (e.g., informal proof, argument, hypothesis).",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context description for the formalization task.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why you chose this source material and context.",
                    },
                    "formalization": {
                        "type": "string",
                        "description": "Only for pure_llm condition: your direct formalization attempt without using the app.",
                    },
                },
                "required": ["source_text", "context", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "refine_context",
            "description": "Refine the session context using the app's context refinement API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["elaborate", "shorten", "formalize", "clarify"],
                        "description": "The refinement action to apply.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decompose",
            "description": "Decompose the source text into proposition nodes using the decomposition API.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_artifact",
            "description": "Generate a formalization artifact of the specified type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {
                        "type": "string",
                        "enum": ["semiformal", "causal-graph", "statistical-model", "property-tests", "dialectical-map"],
                        "description": "The type of artifact to generate.",
                    },
                    "node_id": {
                        "type": "string",
                        "description": "Optional: specific decomposition node ID to formalize.",
                    },
                    "node_label": {
                        "type": "string",
                        "description": "Optional: label for the node being formalized.",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Optional: additional instruction for generation.",
                    },
                },
                "required": ["artifact_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_lean",
            "description": "Generate Lean4 code from the semiformal proof artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Optional: additional instruction for Lean generation.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_lean",
            "description": "Type-check the generated Lean4 code using the verification service.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_whole",
            "description": "Rewrite an entire artifact according to an instruction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {
                        "type": "string",
                        "description": "Which artifact to edit.",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "How to rewrite the artifact.",
                    },
                },
                "required": ["artifact_type", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_inline",
            "description": "Edit a selected portion of an artifact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {
                        "type": "string",
                        "description": "Which artifact to edit.",
                    },
                    "selection_text": {
                        "type": "string",
                        "description": "The text portion to select and edit.",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "How to edit the selected portion.",
                    },
                },
                "required": ["artifact_type", "selection_text", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_artifact",
            "description": "Evaluate the quality and usefulness of a generated artifact. You MUST call this for each artifact before finishing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_type": {
                        "type": "string",
                        "description": "Which artifact to evaluate.",
                    },
                    "useful": {
                        "type": "boolean",
                        "description": "Is this artifact useful for understanding or formalizing the source material?",
                    },
                    "score": {
                        "type": "integer",
                        "description": "Quality score from 1 (poor) to 5 (excellent).",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explain why you gave this score. Be specific about what works and what doesn't.",
                    },
                },
                "required": ["artifact_type", "useful", "score", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "End the session with an overall assessment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "satisfaction": {
                        "type": "integer",
                        "description": "Overall satisfaction score 1-5.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what you accomplished.",
                    },
                    "overall_assessment": {
                        "type": "string",
                        "description": "Compare artifacts if multiple were generated. Which were most/least useful and why?",
                    },
                },
                "required": ["satisfaction", "summary", "overall_assessment"],
            },
        },
    },
]


def _get_artifact_text(state: SessionState, artifact_type: str) -> str | None:
    """Get the text content of an artifact for editing."""
    content = state.artifacts.get(artifact_type)
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return json.dumps(content, indent=2)


def _call_openrouter(
    config: AgentConfig,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call OpenRouter chat completions API with tool definitions."""
    resp = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.openrouter_api_key}",
        },
        json={
            "model": config.agent_model,
            "max_tokens": 4096,
            "messages": messages,
            "tools": TOOLS,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def execute_action(
    action: str,
    params: dict[str, Any],
    state: SessionState,
    client: AppClient,
    config: AgentConfig,
    logger: SessionLogger,
) -> str:
    """Execute an agent action and return a result message for the agent."""

    if action == "generate_input":
        state.source_text = params["source_text"]
        state.context = params["context"]
        state.phase = "input_ready"
        if state.condition == "pure_llm" and params.get("formalization"):
            state.artifacts["pure_llm_formalization"] = params["formalization"]
            state.phase = "artifacts_ready"
            logger.log_step(state.iteration_count, action, params, reasoning=params.get("reasoning", ""))
            return "Source text and context set. Direct formalization stored. Now evaluate your formalization and finish."
        logger.log_step(state.iteration_count, action, params, reasoning=params.get("reasoning", ""))
        return "Source text and context set. Proceed with your workflow."

    if action == "refine_context":
        status, resp = client.refine_context(state.context, params["action"])
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/refine/context", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and "text" in resp:
            state.context = resp["text"]
            state.phase = "context_refined"
            return f"Context refined ({params['action']}). New context: {state.context[:200]}..."
        return f"Context refinement failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "decompose":
        documents = [{"sourceId": "doc-0", "sourceLabel": "Agent Input", "text": state.source_text}]
        status, resp = client.decompose(documents)
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/decomposition/extract", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and "propositions" in resp:
            state.propositions = resp["propositions"]
            state.phase = "decomposed"
            labels = [p.get("label", "?") for p in state.propositions[:5]]
            return f"Decomposed into {len(state.propositions)} nodes: {', '.join(labels)}{'...' if len(state.propositions) > 5 else ''}"
        return f"Decomposition failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "generate_artifact":
        atype = params["artifact_type"]
        status, resp = client.generate_artifact(
            artifact_type=atype,
            source_text=state.source_text,
            context=state.context,
            node_id=params.get("node_id"),
            node_label=params.get("node_label"),
            instruction=params.get("instruction"),
        )
        response_key = ARTIFACT_RESPONSE_KEYS.get(atype, atype)
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint=f"/api/formalization/{atype}", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and response_key in resp:
            state.artifacts[atype] = resp[response_key]
            state.phase = "artifacts_ready"
            content = resp[response_key]
            preview = str(content)[:200] if isinstance(content, str) else json.dumps(content)[:200]
            return f"Generated {atype} artifact. Preview: {preview}..."
        return f"Artifact generation failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "generate_lean":
        semiformal = state.artifacts.get("semiformal")
        if not semiformal:
            return "No semiformal artifact to convert to Lean. Generate a semiformal artifact first."
        status, resp = client.generate_lean(
            informal_proof=semiformal if isinstance(semiformal, str) else json.dumps(semiformal),
            instruction=params.get("instruction"),
        )
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/formalization/lean", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and "leanCode" in resp:
            state.lean_code = resp["leanCode"]
            state.artifacts["lean"] = resp["leanCode"]
            return f"Lean4 code generated. Preview: {state.lean_code[:200]}..."
        return f"Lean generation failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "verify_lean":
        if not state.lean_code:
            return "No Lean code to verify. Generate Lean code first."
        status, resp = client.verify_lean(state.lean_code)
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/verification/lean", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200:
            state.lean_verified = resp.get("valid", False)
            mock = " (mock)" if resp.get("mock") else ""
            return f"Lean verification: valid={state.lean_verified}{mock}"
        return f"Lean verification failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "edit_whole":
        atype = params["artifact_type"]
        text = _get_artifact_text(state, atype)
        if text is None:
            return f"No {atype} artifact to edit."
        status, resp = client.edit_whole(text, params["instruction"])
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/edit/whole", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and "text" in resp:
            state.artifacts[atype] = resp["text"]
            state.phase = "editing"
            return f"Edited {atype} artifact. Preview: {resp['text'][:200]}..."
        return f"Edit failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "edit_inline":
        atype = params["artifact_type"]
        text = _get_artifact_text(state, atype)
        if text is None:
            return f"No {atype} artifact to edit."
        sel_text = params["selection_text"]
        start = text.find(sel_text)
        if start == -1:
            return f"Selection text not found in {atype} artifact."
        end = start + len(sel_text)
        status, resp = client.edit_inline(text, start, end, sel_text, params["instruction"])
        logger.log_step(
            state.iteration_count, action, params,
            api_endpoint="/api/edit/inline", api_status=status,
            api_response_summary=_summarize_response(resp),
            duration_ms=resp.get("_elapsed_ms", 0),
        )
        if status == 200 and "text" in resp:
            state.artifacts[atype] = text[:start] + resp["text"] + text[end:]
            state.phase = "editing"
            return f"Inline edit applied to {atype}. Edited portion: {resp['text'][:200]}..."
        return f"Inline edit failed (status {status}): {resp.get('error', 'unknown')}"

    if action == "evaluate_artifact":
        atype = params["artifact_type"]
        state.artifact_evaluations[atype] = {
            "useful": params["useful"],
            "score": params["score"],
            "reasoning": params["reasoning"],
        }
        state.phase = "evaluating"
        logger.log_step(state.iteration_count, action, params)
        return f"Evaluation recorded for {atype}: score={params['score']}/5, useful={params['useful']}"

    if action == "finish":
        state.phase = "done"
        logger.log_step(state.iteration_count, action, params)
        return "Session complete."

    return f"Unknown action: {action}"


def _summarize_response(resp: dict[str, Any]) -> str:
    """Create a brief summary of an API response for logging."""
    resp_copy = {k: v for k, v in resp.items() if k != "_elapsed_ms"}
    s = json.dumps(resp_copy)
    if len(s) > 300:
        return s[:300] + "..."
    return s


def run_agent_loop(
    state: SessionState,
    client: AppClient,
    config: AgentConfig,
    logger: SessionLogger,
) -> dict[str, Any]:
    """Run the agent decision loop until finish or max iterations."""

    system_prompt = build_system_prompt(state.persona, state.condition)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
    ]

    while state.phase != "done" and state.iteration_count < config.max_iterations:
        state.iteration_count += 1

        user_prompt = build_user_prompt(state.summary_for_agent())
        messages.append({"role": "user", "content": user_prompt})

        if config.verbose:
            print(f"\n--- Iteration {state.iteration_count} (phase: {state.phase}) ---")

        data = _call_openrouter(config, messages)

        choice = data["choices"][0]
        message = choice["message"]

        # Build the assistant message for conversation history
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if message.get("content"):
            assistant_msg["content"] = message["content"]
            if config.verbose:
                print(f"  Agent: {message['content'][:200]}")

        tool_calls = message.get("tool_calls")
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Process tool calls
        if tool_calls:
            for tc in tool_calls:
                action = tc["function"]["name"]
                try:
                    params = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    params = {}

                if config.verbose:
                    print(f"  Action: {action}({json.dumps(params)[:100]})")

                result_text = execute_action(
                    action, params, state, client, config, logger,
                )

                state.history.append({
                    "step": state.iteration_count,
                    "action": action,
                    "params": params,
                })

                if config.verbose:
                    print(f"  Result: {result_text[:200]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_text,
                })

                if state.phase == "done":
                    break
        elif choice.get("finish_reason") == "stop":
            messages.append({
                "role": "user",
                "content": "Please choose a tool action to proceed. If you're done evaluating all artifacts, call the finish tool.",
            })

    return {
        "persona": state.persona.name,
        "condition": state.condition,
        "iterations": state.iteration_count,
        "source_text": state.source_text,
        "context": state.context,
        "artifacts": {k: _artifact_summary(v) for k, v in state.artifacts.items()},
        "evaluations": state.artifact_evaluations,
        "lean_verified": state.lean_verified,
        "finish_data": _extract_finish_data(state.history),
    }


def _artifact_summary(content: Any) -> str:
    """Brief summary of artifact content for results."""
    if isinstance(content, str):
        return content[:500]
    return json.dumps(content)[:500]


def _extract_finish_data(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract the finish action data from the history."""
    for h in reversed(history):
        if h.get("action") == "finish":
            return h.get("params", {})
    return {}
