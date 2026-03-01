# tools/__init__.py
"""
Tool registry with auto-discovery.

To add a new tool:
  1. Create a new .py file in this folder (e.g. tools/calendar.py)
  2. Define your function and decorate it with @register_tool(...)
  3. That's it — it will be picked up automatically on startup.

Each tool file is self-contained: its name, description, parameters,
and Gemini function declaration all live together in one place.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List

from google.genai import types


# ── Internal registry ────────────────────────────────────────────────────────

_HANDLERS: Dict[str, Callable[[Dict[str, Any]], str]] = {}
_DECLARATIONS: List[types.FunctionDeclaration] = []


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
):
    """
    Decorator that registers a function as a Jarvis tool.

    Args:
        name:        Tool name Gemini will call (snake_case).
        description: What the tool does (shown to the model).
        parameters:  JSON-Schema dict describing the args.
                     Use the helper schema() below to build it easily.

    Example:
        @register_tool(
            name="get_time",
            description="Get the current local time.",
            parameters=schema(zone=("string", "IANA timezone, optional")),
        )
        def get_time(args):
            ...
    """
    def decorator(fn: Callable[[Dict[str, Any]], str]):
        _HANDLERS[name] = fn
        _DECLARATIONS.append(
            types.FunctionDeclaration(
                name=name,
                description=description,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        k: types.Schema(type=types.Type.STRING, description=v)
                        for k, v in parameters.items()
                    },
                    required=[
                        k for k, v in parameters.items()
                        if not v.startswith("optional")
                    ],
                ),
            )
        )
        return fn
    return decorator


def schema(**fields: str) -> Dict[str, str]:
    """
    Shorthand for building parameter dicts.
    Mark optional fields by starting the description with 'optional'.

    Example:
        schema(
            query="Search query",
            engine="optional: google | duckduckgo | bing",
        )
    """
    return fields


def run_tool(name: str, args: Dict[str, Any]) -> str:
    handler = _HANDLERS.get(name)
    if not handler:
        return f"[Tool '{name}' not found]"
    try:
        return handler(args or {})
    except Exception as e:
        return f"[Tool '{name}' error: {e}]"


def get_tool_declarations() -> List[types.FunctionDeclaration]:
    """Returns all registered Gemini FunctionDeclarations."""
    return list(_DECLARATIONS)


# ── Auto-discovery ────────────────────────────────────────────────────────────

def _load_all_tools():
    """Import every .py module in this package (except __init__)."""
    package_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        importlib.import_module(f"tools.{module_name}")


_load_all_tools()
