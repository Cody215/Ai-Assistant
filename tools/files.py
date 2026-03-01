# tools/files.py
"""
Tools for creating and managing files on the local machine.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from tools import register_tool, schema


@register_tool(
    name="create_file",
    description="Create or overwrite a file with the given content. Use a relative path (e.g. notes/todo.txt).",
    parameters=schema(
        path="Relative file path, e.g. notes/todo.txt",
        content="Text content to write into the file",
    ),
)
def create_file(args: Dict[str, Any]) -> str:
    rel_path = str(args.get("path", "")).strip()
    content = str(args.get("content", ""))

    if not rel_path:
        return "Missing argument: path"

    p = Path(rel_path)
    if p.is_absolute():
        return "Please use a relative path for safety (e.g. notes/todo.txt)."

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created: {p.resolve()}"


@register_tool(
    name="open_file",
    description="Open an existing file with its default application.",
    parameters=schema(path="Path to the file to open"),
)
def open_file(args: Dict[str, Any]) -> str:
    import os
    path = str(args.get("path", "")).strip()
    if not path:
        return "Missing argument: path"

    p = Path(path)
    if not p.exists():
        return f"File not found: {p}"

    try:
        os.startfile(str(p))  # type: ignore[attr-defined]
        return f"Opened {p.name}."
    except Exception as e:
        return f"Could not open file: {e}"


@register_tool(
    name="draft_email",
    description="Save an email draft as a local text file.",
    parameters=schema(
        to="Recipient email address",
        subject="Email subject line",
        body="Body text of the email",
    ),
)
def draft_email(args: Dict[str, Any]) -> str:
    to      = str(args.get("to", "")).strip() or "unknown"
    subject = str(args.get("subject", "")).strip() or "No subject"
    body    = str(args.get("body", "")).strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"email_draft_{timestamp}.txt"
    draft = f"To: {to}\nSubject: {subject}\n\n{body}\n"

    Path(filename).write_text(draft, encoding="utf-8")
    return f"Email draft saved as {filename}."
