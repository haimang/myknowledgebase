"""Mechanical D03 / PY-50 architecture guards.

These tests deliberately inspect source rather than importing application modules:
an architecture violation must fail deterministically without requiring a database,
an inference endpoint, or any optional runtime dependency.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# D03 §4.1's required v1 layout.  Optional directories (for example data/logs)
# are intentionally not listed here.
REQUIRED_D03_DIRECTORIES = (
    "api",
    "api/internal",
    "api/public",
    "data",
    "data/config",
    "data/database",
    "data/objects",
    "data/prompts",
    "docs/baseline",
    "docs/baseline/domain-truth",
    "docs/baseline/qna-truth",
    "frontend",
    "intake",
    "intake/api",
    "intake/doc",
    "intake/pdf",
    "intake/web",
    "public",
    "src",
    "src/contracts",
    "src/llm_adapters",
    "src/persistence",
    "src/runtime",
    "src/runtime/inference",
    "src/services",
    "src/storage",
    "src/workflows",
    "tests",
    "tests/domain",
    "tests/e2e",
    "tests/unit",
)

REQUIRED_D03_FILES = (
    "docs/baseline/spec-index.md",
    "pyproject.toml",
)

DATABASE_DRIVER_MODULES = frozenset(
    {
        "aiosqlite",
        "libsql",
        "psycopg",
        "psycopg2",
        "sqlalchemy",
        "sqlite3",
        "turso",
    }
)

HTTP_CLIENT_MODULES = frozenset(
    {
        "aiohttp",
        "http.client",
        "httpcore",
        "httpx",
        "requests",
        "urllib.request",
        "urllib3",
    }
)

INFERENCE_SDK_MODULES = frozenset({"openai", "vllm"})

_VLLM_ENDPOINT = re.compile(
    r"(?:^|/)v1/(?:chat/completions|completions|embeddings|responses)(?:$|[/?])",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ImportReference:
    """One import statement, normalized to its absolute package when possible."""

    source: Path
    module: str
    names: tuple[str, ...]
    line: int

    @property
    def location(self) -> str:
        return f"{_relative(self.source)}:{self.line}"

    @property
    def targets(self) -> tuple[str, ...]:
        """Potential imported module paths, including ``from package import child``."""

        children = tuple(f"{self.module}.{name}" for name in self.names if name != "*")
        return (self.module, *children)


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def _python_files(directory: str) -> Iterator[Path]:
    root = REPOSITORY_ROOT / directory
    if not root.exists():
        return
    yield from sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts and ".venv" not in path.parts
    )


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _package_parts(path: Path) -> tuple[str, ...]:
    relative = path.relative_to(REPOSITORY_ROOT).with_suffix("")
    parts = relative.parts
    return parts[:-1]


def _absolute_from_import(path: Path, node: ast.ImportFrom) -> str:
    """Resolve a relative ``from`` module enough for local import guards."""

    if node.level == 0:
        return node.module or ""

    package = _package_parts(path)
    parent_count = node.level - 1
    if parent_count > len(package):
        # Leave malformed/out-of-package imports readable; Python itself will
        # report their runtime error, while the architecture tests stay useful.
        return node.module or ""
    base = package[: len(package) - parent_count]
    module_parts = tuple((node.module or "").split(".")) if node.module else ()
    return ".".join((*base, *module_parts))


def _imports(path: Path) -> tuple[ImportReference, ...]:
    imports: list[ImportReference] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            imports.extend(ImportReference(path, alias.name, (), node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(
                ImportReference(
                    path,
                    _absolute_from_import(path, node),
                    tuple(alias.name for alias in node.names),
                    node.lineno,
                )
            )
    return tuple(imports)


def _dynamic_import_targets(path: Path) -> tuple[tuple[str, int], ...]:
    """Return literal targets passed to importlib.import_module/import_module."""

    targets: list[tuple[str, int]] = []
    for node in ast.walk(_parse(path)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
            continue
        function = _dotted_name(node.func)
        if function in {"import_module", "importlib.import_module"}:
            targets.append((node.args[0].value, node.lineno))
    return tuple(targets)


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_module(module: str, prefixes: Iterable[str]) -> bool:
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


def _import_matches(reference: ImportReference, prefixes: Iterable[str]) -> bool:
    return any(_matches_module(target, prefixes) for target in reference.targets if target)


def _is_persistence_adapter_import(reference: ImportReference) -> bool:
    """Ports are allowed; a concrete persistence package/adapter is not."""

    if reference.module == "src.persistence.ports":
        return False
    if reference.module == "src.persistence" and set(reference.names) <= {"ports"}:
        return False
    return _import_matches(reference, ("src.persistence",))


def _is_database_driver_import(reference: ImportReference) -> bool:
    return _import_matches(reference, DATABASE_DRIVER_MODULES)


def _is_http_or_inference_import(reference: ImportReference) -> bool:
    return _import_matches(reference, (*HTTP_CLIENT_MODULES, *INFERENCE_SDK_MODULES))


def _literal_strings(nodes: Iterable[ast.AST]) -> Iterator[str]:
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                yield child.value


def _direct_vllm_http_calls(path: Path) -> tuple[int, ...]:
    """Catch endpoint calls even if a HTTP client arrived through indirection."""

    violations: list[int] = []
    http_verbs = {"delete", "get", "patch", "post", "put", "request", "send", "stream", "urlopen"}
    for node in ast.walk(_parse(path)):
        if not isinstance(node, ast.Call):
            continue
        method = _dotted_name(node.func).rsplit(".", maxsplit=1)[-1].casefold()
        if method not in http_verbs:
            continue
        if any(_VLLM_ENDPOINT.search(value) or "vllm" in value.casefold() for value in _literal_strings(node.args)):
            violations.append(node.lineno)
    return tuple(violations)


def _legacy_import(module: str) -> bool:
    normalized = module.casefold().replace("_", "-")
    return (
        normalized.startswith("context.legacy")
        or normalized.startswith("legacy-family")
        or normalized.startswith("legacy-python")
        or normalized.startswith("legacy-specs")
    )


def _symbol_words(name: str) -> set[str]:
    snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).casefold()
    return {word for word in snake.split("_") if word}


def _workflow_implementation_violations(path: Path) -> tuple[tuple[int, str], ...]:
    """Identify executable runtime mechanics while allowing declarative fields."""

    violations: list[tuple[int, str]] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            words = _symbol_words(node.name)
            if {"claim", "outbox", "retry"} & words:
                violations.append((node.lineno, node.name))
        elif isinstance(node, ast.ClassDef):
            words = _symbol_words(node.name)
            # A declarative RetryPolicy value object may be described elsewhere;
            # claim/outbox classes are runtime infrastructure in every case.
            if {"claim", "outbox"} & words:
                violations.append((node.lineno, node.name))
        elif isinstance(node, ast.Call):
            symbol = _dotted_name(node.func)
            final_name = symbol.rsplit(".", maxsplit=1)[-1]
            words = _symbol_words(final_name)
            # ``RetryPolicy(...)`` is a declarative value-object constructor,
            # whereas lowercase retry calls are executable retry mechanics.
            retry_implementation = "retry" in words and not final_name[:1].isupper()
            if {"claim", "outbox"} & words or retry_implementation:
                violations.append((node.lineno, symbol))
    return tuple(violations)


def _route_path_from_decorator(decorator: ast.AST) -> str | None:
    if not isinstance(decorator, ast.Call):
        return None
    method = _dotted_name(decorator.func).rsplit(".", maxsplit=1)[-1].casefold()
    if method not in {"api_route", "delete", "get", "patch", "post", "put"}:
        return None
    if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
        return decorator.args[0].value
    return None


def _public_route_paths(path: Path) -> tuple[tuple[int, str], ...]:
    routes: list[tuple[int, str]] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for decorator in node.decorator_list:
                route_path = _route_path_from_decorator(decorator)
                if route_path is not None:
                    routes.append((node.lineno, route_path))
        elif isinstance(node, ast.Call) and _dotted_name(node.func).rsplit(".", maxsplit=1)[-1] == "APIRouter":
            for keyword in node.keywords:
                if (
                    keyword.arg == "prefix"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    routes.append((node.lineno, keyword.value.value))
    return tuple(routes)


def _is_forbidden_public_path(path: str) -> bool:
    segments = {segment.casefold() for segment in path.split("/") if segment}
    return bool({"oauth", "ui", "workflow", "workflows"} & segments)


def _oauth_symbols(path: Path) -> tuple[int, ...]:
    violations: list[int] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            if any("oauth" in alias.name.casefold() for alias in node.names):
                violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "oauth" in module.casefold() or any("oauth" in alias.name.casefold() for alias in node.names):
                violations.append(node.lineno)
        elif isinstance(node, ast.Name | ast.Attribute):
            value = node.id if isinstance(node, ast.Name) else node.attr
            if "oauth" in value.casefold():
                violations.append(node.lineno)
    return tuple(violations)


def test_d03_required_tree_exists() -> None:
    missing_directories = [path for path in REQUIRED_D03_DIRECTORIES if not (REPOSITORY_ROOT / path).is_dir()]
    missing_files = [path for path in REQUIRED_D03_FILES if not (REPOSITORY_ROOT / path).is_file()]

    assert not missing_directories, f"D03 required directories are missing: {', '.join(missing_directories)}"
    assert not missing_files, f"D03 required files are missing: {', '.join(missing_files)}"


def test_contracts_are_substantive_not_an_empty_package() -> None:
    contract_modules = []
    for path in _python_files("src/contracts"):
        if path.name == "__init__.py":
            continue
        tree = _parse(path)
        if any(isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) for node in ast.walk(tree)):
            contract_modules.append(_relative(path))

    assert contract_modules, "src/contracts must contain at least one substantive schema or validator module"


def test_services_do_not_reach_api_concrete_persistence_or_inference_transport() -> None:
    violations: list[str] = []
    for path in _python_files("src/services"):
        for reference in _imports(path):
            if _import_matches(reference, ("api",)):
                violations.append(f"{reference.location} imports API module {reference.module}")
            if _is_persistence_adapter_import(reference):
                violations.append(f"{reference.location} imports concrete persistence {reference.module}")
            if _is_database_driver_import(reference):
                violations.append(f"{reference.location} imports database driver {reference.module}")
            if _import_matches(reference, ("src.llm_adapters", "llm_adapters")):
                violations.append(f"{reference.location} imports LLM adapter {reference.module}")
            if _is_http_or_inference_import(reference):
                violations.append(f"{reference.location} imports HTTP/inference client {reference.module}")
        for module, line in _dynamic_import_targets(path):
            if _matches_module(module, (*HTTP_CLIENT_MODULES, *INFERENCE_SDK_MODULES)):
                violations.append(f"{_relative(path)}:{line} dynamically imports HTTP/inference client {module}")
        for line in _direct_vllm_http_calls(path):
            violations.append(f"{_relative(path)}:{line} calls a vLLM/OpenAI-compatible HTTP endpoint")

    assert not violations, "D03/PY-13/PY-14 service boundary violations:\n" + "\n".join(violations)


def test_contracts_do_not_import_runtime_or_io_layers() -> None:
    forbidden_layers = ("src.runtime", "src.services", "src.persistence", "src.storage")
    violations = [
        f"{reference.location} imports {reference.module}"
        for path in _python_files("src/contracts")
        for reference in _imports(path)
        if _import_matches(reference, forbidden_layers)
    ]

    assert not violations, "D03 contracts must stay pure:\n" + "\n".join(violations)


def test_runtime_does_not_import_legacy_context() -> None:
    violations: list[str] = []
    for path in _python_files("src/runtime"):
        for reference in _imports(path):
            if any(_legacy_import(target) for target in reference.targets):
                violations.append(f"{reference.location} imports legacy target {reference.module}")
            if _is_database_driver_import(reference):
                violations.append(f"{reference.location} imports database driver {reference.module}")
        for module, line in _dynamic_import_targets(path):
            if _legacy_import(module):
                violations.append(f"{_relative(path)}:{line} dynamically imports legacy target {module}")

    assert not violations, "D03/PY-15 runtime legacy imports are forbidden:\n" + "\n".join(violations)


def test_workflows_contain_declarations_not_claim_outbox_or_retry_implementation() -> None:
    violations = [
        f"{_relative(path)}:{line} runtime implementation symbol {symbol!r}"
        for path in _python_files("src/workflows")
        for line, symbol in _workflow_implementation_violations(path)
    ]

    assert not violations, "D03 workflows must remain declarative:\n" + "\n".join(violations)


def test_public_routes_do_not_expose_ui_workflow_or_oauth_surface() -> None:
    """Keep the early public-route guard narrow until the full S01 route ledger lands."""

    violations: list[str] = []
    for path in _python_files("api/public"):
        for line, route_path in _public_route_paths(path):
            if _is_forbidden_public_path(route_path):
                violations.append(f"{_relative(path)}:{line} exposes forbidden public route {route_path!r}")
        for line in _oauth_symbols(path):
            violations.append(f"{_relative(path)}:{line} uses OAuth in api/public")

    assert not violations, "D03 public API expansion is forbidden:\n" + "\n".join(violations)
