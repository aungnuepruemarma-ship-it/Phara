"""Execution Geometry Analyzer.

Runs a code snippet inside the sandbox under a sys.settrace + ast harness and
returns geometric features of the execution:
  ast_nodes, ast_depth, n_functions, call_counts, call_graph edges,
  line_hits histogram, max_call_depth, total_line_events.

The harness is injected as a wrapper script; the user code runs as __main__-like
top-level inside exec(). Geometry is emitted on a marker line as JSON so it can
coexist with the code's own stdout.
"""
from __future__ import annotations

import json

from . import sandbox

_MARKER = "===SCILOOP_GEOMETRY==="

_HARNESS = r'''
import ast, json, sys

_SRC = {src!r}

# ---- static geometry (AST) ----
def _ast_stats(src):
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {{"ast_error": str(e)[:200]}}
    n = 0
    max_d = 0
    fns = []
    def walk(node, d):
        nonlocal n, max_d
        n += 1
        max_d = max(max_d, d)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns.append(node.name)
        for c in ast.iter_child_nodes(node):
            walk(c, d + 1)
    walk(tree, 0)
    return {{"ast_nodes": n, "ast_depth": max_d, "n_functions": len(fns), "functions": fns[:30]}}

_static = _ast_stats(_SRC)

# ---- dynamic geometry (settrace) ----
_line_hits = {{}}
_call_counts = {{}}
_edges = {{}}
_stack = ["<top>"]
_depth = 0
_max_depth = 0
_events = 0

def _tracer(frame, event, arg):
    global _depth, _max_depth, _events
    _events += 1
    if _events > 2_000_000:
        sys.settrace(None)
        return None
    name = frame.f_code.co_name
    if event == "call":
        caller = _stack[-1] if _stack else "<top>"
        _call_counts[name] = _call_counts.get(name, 0) + 1
        key = caller + "->" + name
        _edges[key] = _edges.get(key, 0) + 1
        _stack.append(name)
        _depth += 1
        _max_depth = max(_max_depth, _depth)
    elif event == "return":
        if _stack:
            _stack.pop()
        _depth = max(0, _depth - 1)
    elif event == "line":
        ln = frame.f_lineno
        _line_hits[ln] = _line_hits.get(ln, 0) + 1
    return _tracer

_err = None
sys.settrace(_tracer)
try:
    exec(compile(_SRC, "<experiment>", "exec"), {{"__name__": "__sciloop__"}})
except BaseException as e:
    _err = type(e).__name__ + ": " + str(e)[:200]
finally:
    sys.settrace(None)

_geom = dict(_static)
_geom.update({{
    "total_line_events": sum(_line_hits.values()),
    "distinct_lines": len(_line_hits),
    "max_call_depth": _max_depth,
    "call_counts": dict(sorted(_call_counts.items(), key=lambda kv: -kv[1])[:20]),
    "call_graph": dict(sorted(_edges.items(), key=lambda kv: -kv[1])[:30]),
    "runtime_error": _err,
}})
print("{marker}" + json.dumps(_geom))
'''


def run_with_geometry(code: str, timeout: int = 15) -> dict:
    """Execute code in the sandbox with tracing. Returns the sandbox result dict
    plus a 'geometry' key (dict or None) with stdout cleaned of the marker."""
    harness = _HARNESS.format(src=code, marker=_MARKER)
    result = sandbox.run_code(harness, timeout=timeout)

    geometry = None
    clean_lines = []
    for line in (result.get("stdout") or "").splitlines():
        if line.startswith(_MARKER):
            try:
                geometry = json.loads(line[len(_MARKER):])
            except json.JSONDecodeError:
                geometry = None
        else:
            clean_lines.append(line)
    result["stdout"] = "\n".join(clean_lines)
    result["geometry"] = geometry
    # Surface in-experiment errors captured by the harness
    if geometry and geometry.get("runtime_error") and result.get("exit_code") == 0:
        result["experiment_error"] = geometry["runtime_error"]
    return result
