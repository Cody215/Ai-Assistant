# tools/web.py
"""
Tools for web-based actions.
"""

import urllib.parse
import webbrowser
from typing import Any, Dict

from tools import register_tool, schema


@register_tool(
    name="web_search",
    description="Open a browser search for the given query.",
    parameters=schema(
        query="The search query",
        engine="optional: google | duckduckgo | bing (default: google)",
    ),
)
def web_search(args: Dict[str, Any]) -> str:
    query  = str(args.get("query", "")).strip()
    engine = str(args.get("engine", "google")).strip().lower()

    if not query:
        return "Missing argument: query"

    q = urllib.parse.quote_plus(query)

    urls = {
        "duckduckgo": f"https://duckduckgo.com/?q={q}",
        "ddg":        f"https://duckduckgo.com/?q={q}",
        "bing":       f"https://www.bing.com/search?q={q}",
    }
    url = urls.get(engine, f"https://www.google.com/search?q={q}")

    webbrowser.open(url)
    return f"Searching {engine} for: {query}"
