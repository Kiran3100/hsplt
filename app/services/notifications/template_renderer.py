"""Simple {{variable}} template rendering for notification body/subject."""
import re
from typing import Any


def render_template(template: str, payload: dict[str, Any]) -> str:
    """Replace {{key}} with payload.get('key', '')."""
    if not payload:
        return template
    def repl(match):
        key = match.group(1).strip()
        return str(payload.get(key, ""))
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", repl, template)
