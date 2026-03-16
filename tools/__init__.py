# tools/__init__.py
"""
Tool registry with auto-discovery.

On import, this module scans the tools/ directory and imports every .py
file it finds (except __init__.py). Each file registers its tools using
the @register_tool decorator, which:
  1. Stores the handler function in _HANDLERS (name → callable)
  2. Builds a Gemini FunctionDeclaration and appends it to _DECLARATIONS

jarvis_core passes _DECLARATIONS to Gemini at startup so the model knows
what tools are available. When Gemini returns a FunctionCall, jarvis_core
calls run_tool(name, args) which looks up and executes the handler.

To add a new tool:
1. Create a new .py file in tools/ (e.g. tools/calendar.py)
2. Import register_tool and schema from tools
3. Decorate your function:

    @register_tool(
        name="my_tool",
        description="What this tool does — shown to Gemini.",
        parameters=schema(
            required_arg="Description of this argument",
            optional_arg="optional: description of optional argument",
        ),
    )
    def my_tool(args: dict) -> str:
        value = args.get("required_arg", "")
        return f"Result: {value}"

4. Restart Jarvis — the tool is automatically discovered and registered.

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

    Builds a Gemini FunctionDeclaration from the parameters dict
    so the model knows the tool's name, purpose, and argument types.

    Parameters marked with descriptions starting with "optional"
    are excluded from the required fields list.
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

    Usage:
        schema(
            query="The search query",
            engine="optional: google | duckduckgo | bing",
        )
    """
    return fields


def run_tool(name: str, args: Dict[str, Any]) -> str:
    """
    Execute a registered tool by name with the given args.
    Always returns a string — never raises.
    """
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
