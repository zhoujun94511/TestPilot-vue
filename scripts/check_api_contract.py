#!/usr/bin/env python3
"""
Lightweight API contract checker for TestPilot.

Checks:
1) Backend routes (blueprints) vs frontend API paths usage.
2) Frontend method usage vs backend allowed methods (the best effort).
3) Exported API functions vs references in views/components/composables/stores
   (and cross-module use within frontend/src/api).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINTS_DIR = ROOT / "blueprints"
FRONTEND_API_DIR = ROOT / "frontend" / "src" / "api"
FRONTEND_CONSUMER_DIRS = (
    ROOT / "frontend" / "src" / "views",
    ROOT / "frontend" / "src" / "components",
    ROOT / "frontend" / "src" / "composables",
    ROOT / "frontend" / "src" / "stores",
)
API_HELPER_MODULES = {"http.ts", "core.ts"}

# Routes in this set are intentionally not consumed by frontend API layer:
# - internal fallback endpoints
# - operation-specific orchestration endpoints that require server-side assembled payload
IGNORED_BACKEND_ONLY: Set[str] = {
    "/api/chat/save-ai-message",
    "/api/export/batch",
}

# Public API aliases or optional entry points — not required to appear in views yet.
IGNORED_UNUSED_API_EXPORTS: Set[str] = {
    "validateConfigItem",
    "getConfigCategories",
    "getConfigsByCategory",
    "saveConfigsByCategory",
    "exportConfigs",
    "getConfigItem",
    "getChatSuggestions",
    "getChatTemplates",
    "resolveAnalysisRequirements",
}


@dataclass
class RouteDef:
    file: str
    path: str
    methods: Set[str]


@dataclass
class FrontCall:
    file: str
    method: str
    path: str


@dataclass
class ApiExport:
    file: str
    name: str


def _route_prefixes() -> Dict[str, str]:
    mapping: Dict[str, str] = {}

    # 1) Parse prefixes from blueprint definitions.
    bp_def_re = re.compile(
        r"(\w+)\s*=\s*Blueprint\([^)]*url_prefix\s*=\s*['\"]([^'\"]+)['\"]"
    )
    for py in BLUEPRINTS_DIR.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for m in bp_def_re.finditer(text):
            mapping[m.group(1)] = m.group(2)

    # 2) Parse overrides from app register_blueprint(..., url_prefix=...).
    app_py = (ROOT / "app.py").read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(
        r"register_blueprint\((\w+),\s*url_prefix=['\"]([^'\"]+)['\"]\)", app_py
    ):
        mapping[m.group(1)] = m.group(2)

    return mapping


def parse_backend_routes() -> List[RouteDef]:
    prefixes = _route_prefixes()
    out: List[RouteDef] = []
    route_re = re.compile(
        r"@(\w+)\.route\(\s*['\"]([^'\"]+)['\"](?:,\s*methods\s*=\s*\[([^]]+)])?"
    )
    for py in BLUEPRINTS_DIR.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for m in route_re.finditer(text):
            bp_var = m.group(1)
            sub_path = m.group(2)
            methods_raw = m.group(3)
            if methods_raw:
                methods = {
                    s.strip().strip("'\"").upper()
                    for s in methods_raw.split(",")
                    if s.strip()
                }
            else:
                methods = {"GET"}

            if bp_var in prefixes:
                full = f"{prefixes[bp_var]}{sub_path}"
            else:
                # Already full-prefixed in blueprint or fallback.
                full = sub_path if sub_path.startswith("/api/") else f"/api{sub_path}"

            out.append(RouteDef(file=py.name, path=full, methods=methods))
    return out


def parse_frontend_calls() -> List[FrontCall]:
    out: List[FrontCall] = []
    seen: Set[Tuple[str, str, str]] = set()
    call_re = re.compile(
        r"\b(get|post|put|del)\s*<[^>]*>?\s*\(\s*[`'\"]([^`'\"]+)[`'\"]",
        re.IGNORECASE,
    )
    call_re_simple = re.compile(
        r"\b(get|post|put|del)\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", re.IGNORECASE
    )
    download_re = re.compile(
        r"\bdownload\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", re.IGNORECASE
    )
    request_re = re.compile(r"\bhttp\.request\s*<[^>]*>?\s*\(\s*\{([^}]*)}", re.IGNORECASE | re.DOTALL)
    request_re_simple = re.compile(r"\bhttp\.request\s*\(\s*\{([^}]*)}", re.IGNORECASE | re.DOTALL)
    request_url_re = re.compile(r"url\s*:\s*[`'\"]([^`'\"]+)[`'\"]", re.IGNORECASE)
    request_method_re = re.compile(r"method\s*:\s*[`'\"]([A-Za-z]+)[`'\"]", re.IGNORECASE)
    request_url_fn_re = re.compile(r"url\s*:\s*(\w+)\s*\(", re.IGNORECASE)
    fetch_sse_re = re.compile(r"\bfetchSse\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", re.IGNORECASE)
    path_fn_re = re.compile(r"function\s+(\w+)\s*\([^)]*\)\s*\{([^}]*)}", re.IGNORECASE | re.DOTALL)
    path_return_re = re.compile(r"return\s+[`'\"]([^`'\"]+)[`'\"]", re.IGNORECASE)
    for ts in FRONTEND_API_DIR.glob("*.ts"):
        text = ts.read_text(encoding="utf-8", errors="ignore")
        fn_paths: Dict[str, Set[str]] = {}
        for fn_match in path_fn_re.finditer(text):
            fn_name = fn_match.group(1)
            fn_body = fn_match.group(2)
            literals = {m.group(1) for m in path_return_re.finditer(fn_body)}
            if literals:
                fn_paths[fn_name] = literals
        for m in call_re.finditer(text):
            call = FrontCall(file=ts.name, method=m.group(1).upper(), path=m.group(2))
            key = (call.file, call.method, call.path)
            if key not in seen:
                seen.add(key)
                out.append(call)
        for m in call_re_simple.finditer(text):
            call = FrontCall(file=ts.name, method=m.group(1).upper(), path=m.group(2))
            key = (call.file, call.method, call.path)
            if key not in seen:
                seen.add(key)
                out.append(call)
        for m in download_re.finditer(text):
            call = FrontCall(file=ts.name, method="GET", path=m.group(1))
            key = (call.file, call.method, call.path)
            if key not in seen:
                seen.add(key)
                out.append(call)
        for req in list(request_re.finditer(text)) + list(request_re_simple.finditer(text)):
            block = req.group(1)
            url_match = request_url_re.search(block)
            method_match = request_method_re.search(block)
            method = (method_match.group(1).upper() if method_match else "GET")
            if url_match:
                call = FrontCall(file=ts.name, method=method, path=url_match.group(1))
                key = (call.file, call.method, call.path)
                if key not in seen:
                    seen.add(key)
                    out.append(call)
                continue
            fn_match = request_url_fn_re.search(block)
            if fn_match:
                fn_name = fn_match.group(1)
                for p in fn_paths.get(fn_name, set()):
                    call = FrontCall(file=ts.name, method=method, path=p)
                    key = (call.file, call.method, call.path)
                    if key not in seen:
                        seen.add(key)
                        out.append(call)
        for m in fetch_sse_re.finditer(text):
            call = FrontCall(file=ts.name, method="POST", path=m.group(1))
            key = (call.file, call.method, call.path)
            if key not in seen:
                seen.add(key)
                out.append(call)
    return out


def parse_api_exports() -> List[ApiExport]:
    out: List[ApiExport] = []
    fn_patterns = (
        re.compile(r"export\s+async\s+function\s+(\w+)", re.MULTILINE),
        re.compile(r"export\s+function\s+(\w+)", re.MULTILINE),
    )
    for ts in sorted(FRONTEND_API_DIR.glob("*.ts")):
        if ts.name in API_HELPER_MODULES:
            continue
        text = ts.read_text(encoding="utf-8", errors="ignore")
        seen: Set[str] = set()
        for pattern in fn_patterns:
            for m in pattern.finditer(text):
                name = m.group(1)
                if name in seen:
                    continue
                seen.add(name)
                out.append(ApiExport(file=ts.name, name=name))
    return out


def _iter_consumer_source_files() -> Iterable[Path]:
    for base in FRONTEND_CONSUMER_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in {".vue", ".ts", ".tsx"}:
                continue
            yield path
    for ts in FRONTEND_API_DIR.glob("*.ts"):
        if ts.name not in API_HELPER_MODULES:
            yield ts


def build_usage_blob() -> str:
    chunks: List[str] = []
    for path in _iter_consumer_source_files():
        chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def export_is_referenced(name: str, defining_file: str, blob: str) -> bool:
    if name in IGNORED_UNUSED_API_EXPORTS:
        return True
    # Import lists and call sites in consumers + other api modules.
    if re.search(rf"\b{re.escape(name)}\b", blob) is None:
        return False
    # Must appear outside its defining module (avoid counting the export line only).
    module_text = (FRONTEND_API_DIR / defining_file).read_text(encoding="utf-8", errors="ignore")
    without_def = re.sub(rf"export\s+async\s+function\s+{re.escape(name)}\b", "", module_text)
    without_def = re.sub(rf"export\s+function\s+{re.escape(name)}\b", "", without_def)
    external = blob.replace(module_text, without_def, 1)
    return re.search(rf"\b{re.escape(name)}\b", external) is not None


def find_unused_api_exports() -> List[ApiExport]:
    blob = build_usage_blob()
    unused: List[ApiExport] = []
    for item in parse_api_exports():
        if not export_is_referenced(item.name, item.file, blob):
            unused.append(item)
    return unused


def normalize_method(method: str) -> str:
    return "DELETE" if method == "DEL" else method


def normalize_front_path(path: str) -> str:
    # Turn TS template placeholders into flask-like dynamic segments.
    p = re.sub(r"\$\{[^}]+}", "<param>", path)
    return p


def normalize_backend_path(path: str) -> str:
    return re.sub(r"<[^>]+>", "<param>", path)


def main() -> int:
    strict_exports = os.environ.get("STRICT_API_EXPORTS", "").strip() in {"1", "true", "yes"}
    routes = parse_backend_routes()
    calls = parse_frontend_calls()
    unused_exports = find_unused_api_exports()

    route_by_path: Dict[str, Set[str]] = {}
    for r in routes:
        route_by_path.setdefault(normalize_backend_path(r.path), set()).update(r.methods)

    path_missing: List[FrontCall] = []
    method_mismatch: List[Tuple[FrontCall, Set[str]]] = []
    frontend_paths: Set[str] = set()

    for c in calls:
        if not c.path.startswith("/"):
            continue
        raw_path = normalize_front_path(c.path)
        path = f"/api{raw_path}" if not raw_path.startswith("/api/") else raw_path
        frontend_paths.add(path)
        if path not in route_by_path:
            path_missing.append(c)
            continue
        expected = route_by_path[path]
        if normalize_method(c.method) not in expected:
            method_mismatch.append((c, expected))

    backend_only: List[RouteDef] = []
    for r in routes:
        normalized_path = normalize_backend_path(r.path)
        if normalized_path in IGNORED_BACKEND_ONLY:
            continue
        if normalized_path not in frontend_paths:
            backend_only.append(r)

    print("== API Contract Check ==")
    print(f"Backend routes: {len(routes)}")
    print(f"Frontend calls: {len(calls)}")
    print(f"API exported functions: {len(parse_api_exports())}")
    print()

    if not path_missing and not method_mismatch:
        print("No obvious path/method mismatches found.")

    if path_missing:
        print("[Path missing in backend]")
        for c in path_missing:
            print(f"- {c.file}: {c.method} {c.path}")
        print()

    if method_mismatch:
        print("[Method mismatch]")
        for c, exp in method_mismatch:
            allowed = ",".join(sorted(exp))
            print(f"- {c.file}: {c.method} {c.path} (allowed: {allowed})")
        print()

    if backend_only:
        print("[Backend routes not called by frontend API layer]")
        for r in sorted(backend_only, key=lambda x: x.path):
            methods = ",".join(sorted(r.methods))
            print(f"- {r.file}: {methods} {r.path}")
        print()

    if unused_exports:
        print("[API exports with no detected usage in views/components/composables/stores]")
        for item in sorted(unused_exports, key=lambda x: (x.file, x.name)):
            print(f"- {item.file}: {item.name}")
        print("  (Set STRICT_API_EXPORTS=1 to fail CI on this section.)")
        print()

    fail_exports = strict_exports and bool(unused_exports)
    return 1 if (path_missing or method_mismatch or fail_exports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
