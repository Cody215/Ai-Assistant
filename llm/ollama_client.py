# llm/ollama_client.py
"""
Ollama client for local text inference and simple tool calls.

Handles the Ollama API format differences from Gemini:
  - Tools passed as JSON schema dicts, not FunctionDeclaration objects
  - Response is a dict, not a typed object
  - No built-in session history — stateless per call

Only called for tools declared routing="local".
Falls back gracefully if Ollama is unavailable.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Tuple


def _build_ollama_tools(declarations) -> List[Dict]:
    """
    Convert Gemini FunctionDeclaration objects to Ollama tool schema format.
    Ollama expects standard OpenAI-style JSON schema tool definitions.
    """
    ollama_tools = []
    for decl in declarations:
        properties = {}
        required   = []

        if decl.parameters and decl.parameters.properties:
            for prop_name, prop_schema in decl.parameters.properties.items():
                properties[prop_name] = {
                    "type":        "string",
                    "description": prop_schema.description or "",
                }
            if decl.parameters.required:
                required = list(decl.parameters.required)

        ollama_tools.append({
            "type": "function",
            "function": {
                "name":        decl.name,
                "description": decl.description or "",
                "parameters": {
                    "type":       "object",
                    "properties": properties,
                    "required":   required,
                },
            },
        })
    return ollama_tools


def call_with_tool(
    model: str,
    user_text: str,
    system_prompt: str,
    declarations,
    host: str = "http://localhost:11434",
) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Send a query to Ollama with tool definitions.

    Returns a tuple of (tool_name, None, tool_args) if a tool was called,
    or (None, response_text, None) for a plain text response,
    or (None, None, None) on failure — caller should fall back to Gemini.
    """
    try:
        import ollama

        ollama_tools = _build_ollama_tools(declarations)

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_text},
            ],
            tools=ollama_tools,
        )

        message = response.get("message", {})

        # Check for tool call in response
        tool_calls = message.get("tool_calls")
        if tool_calls:
            call      = tool_calls[0]
            fn        = call.get("function", {})
            tool_name = fn.get("name", "")
            tool_args = fn.get("arguments", {})
            if isinstance(tool_args, str):
                import json
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {}
            return tool_name, None, tool_args

        # Plain text response
        text = message.get("content", "").strip()
        return None, text, None

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        err = str(e).lower()
        if "connection" in err or "refused" in err:
            logger.warning(
                "[Ollama] Not reachable — falling back to Gemini. (Is Ollama running? Try: ollama serve)"
            )
        else:
            logger.exception(f"[Ollama] Error: {e} — falling back to Gemini.")
        return None, None, None