"""Self-authored tools (Voyager-style skill library).

Lets the agent extend its OWN toolset at runtime: it proposes a new tool (name,
description, JSON-schema params, and a Python function body), which is validated,
written to agent/tools/generated/, and dynamically registered. Creation is
approval-gated and the source is shown to the founder before it goes live.

Safety: only a whitelist of imports is permitted and dangerous builtins
(eval/exec/open/__import__/compile) are rejected at validation time. This is a
guardrail, not a full sandbox — creation stays behind the approval gate.
"""
import ast
import importlib
import importlib.util
import os
import re

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "tools", "generated")

ALLOWED_IMPORTS = {
    "json", "re", "math", "datetime", "statistics", "time", "random",
    "requests", "collections", "itertools", "urllib",
}
BLOCKED_NAMES = {"eval", "exec", "compile", "__import__", "open", "input"}

_TEMPLATE = '''"""Auto-generated tool: {name}. Created by the agent."""
from agent.registry import register

{imports}

@register(
    name={name!r},
    description={description!r},
    parameters={params!r},
    category="generated",
)
def {name}(**kwargs):
{body}
'''


def _safe_name(name: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,40}", name or ""):
        raise ValueError("Tool name must be snake_case, 3-41 chars, e.g. 'currency_convert'.")
    return name


def _validate(source: str):
    tree = ast.parse(source)  # raises SyntaxError if invalid
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = (getattr(node, "module", None) or "")
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [mod.split(".")[0]]
            for n in names:
                if n and n not in ALLOWED_IMPORTS and n != "agent":
                    raise ValueError(f"Import '{n}' is not allowed in generated tools.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"Use of '{node.id}' is not allowed in generated tools.")
        if isinstance(node, ast.Attribute) and node.attr in {"system", "popen", "remove", "rmdir", "unlink"}:
            raise ValueError(f"Call to '{node.attr}' is not allowed in generated tools.")


def build_source(name: str, description: str, params: dict, body: str,
                 imports: str = "") -> str:
    name = _safe_name(name)
    if not (body or "").strip():
        raise ValueError("Generated tools require a non-empty Python function body.")
    indented = "\n".join("    " + line for line in body.splitlines())
    src = _TEMPLATE.format(name=name, description=description, params=params or {"type": "object", "properties": {}},
                           body=indented, imports=imports.strip())
    _validate(src)
    return src


def install_tool(name: str, source: str) -> dict:
    """Write a validated generated tool to disk and register it immediately."""
    os.makedirs(GENERATED_DIR, exist_ok=True)
    init_path = os.path.join(GENERATED_DIR, "__init__.py")
    if not os.path.exists(init_path):
        open(init_path, "w", encoding="utf-8").close()
    path = os.path.join(GENERATED_DIR, f"{name}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    # Import the module so its @register decorator runs.
    spec = importlib.util.spec_from_file_location(f"agent.tools.generated.{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"installed": True, "name": name, "path": path}


def load_generated():
    """Import all previously-created generated tools (call once at startup)."""
    if not os.path.isdir(GENERATED_DIR):
        return 0
    count = 0
    for fname in os.listdir(GENERATED_DIR):
        if fname.endswith(".py") and fname != "__init__.py":
            name = fname[:-3]
            try:
                path = os.path.join(GENERATED_DIR, fname)
                spec = importlib.util.spec_from_file_location(f"agent.tools.generated.{name}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                count += 1
            except Exception:
                pass
    return count
