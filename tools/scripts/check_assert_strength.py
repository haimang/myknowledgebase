#!/usr/bin/env python3
"""FF-F7-06: 断言强度门禁 (防假绿制度化, [Q7])。

AST 扫描每个 `def test_*`, 若其断言**全部**为弱断言 (status==200 / x!="" /
x is not None / len(x)>=N / .strip()!="" 等仅证"流转/非空"的模式) 而无任何
语义/安全/时间/向量真实性断言, 则判为结构性假绿 → 报 file:line 并使 CI 失败。
允许弱断言作为前置 (只要同函数还有 ≥1 条强断言)。

用法: python3 tools/scripts/check_assert_strength.py [path ...]   (默认 tests/)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _is_weak(node: ast.expr) -> bool:
    """判定单条 assert 是否**仅证流转/非空** (弱)。

    弱 = 只确认"成功/存在/非空/计数", 不验证内容/语义:
      · `... is not None`     (存在性)
      · `... == 200/201/204`  (HTTP 成功码)
      · `... != ""`           (非空)
      · `len(...) >= / > N`   (单纯计数)
      · `assert <name>`       (truthiness)
    非弱 (强, 验证了具体预期结果, 不判弱):
      · `... is None` (断言被拒绝)、`== ""`/`== <value>` (断言具体输出)、
        `== <exact N>` (精确计数)、in/not-in、调用断言 (raises 等)。
    """
    if isinstance(node, ast.Name):
        return True  # assert x — 仅 truthiness
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op, comp = node.ops[0], node.comparators[0]
        if isinstance(op, ast.IsNot) and isinstance(comp, ast.Constant) and comp.value is None:
            return True  # is not None
        if isinstance(op, ast.NotEq) and isinstance(comp, ast.Constant) and comp.value == "":
            return True  # != ""
        if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and comp.value in (200, 201, 204):
            return True  # == HTTP 成功码
        if isinstance(op, (ast.GtE, ast.Gt)) and isinstance(node.left, ast.Call):
            f = node.left.func
            if isinstance(f, ast.Name) and f.id == "len":
                return True  # len(...) >= N
    return False


def _classify(func: ast.FunctionDef) -> tuple[int, int]:
    weak = strong = 0
    for n in ast.walk(func):
        if isinstance(n, ast.Assert):
            test = n.test
            # status_code==200 内嵌于属性比较时, _is_weak 仍命中 Compare。
            if _is_weak(test):
                weak += 1
            else:
                strong += 1
    return weak, strong


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            weak, strong = _classify(node)
            if weak > 0 and strong == 0:
                violations.append(f"{path}:{node.lineno}: {node.name} — 仅弱断言 (weak={weak}, strong=0)")
    return violations


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path("tests")]
    files: list[Path] = []
    for root in roots:
        files.extend(root.rglob("test_*.py") if root.is_dir() else [root])
    # smoke 测试是刻意的浅 boot/import 健全性检查, 不在断言强度门禁范围。
    files = [f for f in files if "/smoke/" not in str(f).replace("\\", "/")]
    all_violations: list[str] = []
    for f in sorted(files):
        all_violations.extend(scan_file(f))
    if all_violations:
        print("断言强度门禁失败 (仅弱断言的测试, 见 ⛔1):")
        for v in all_violations:
            print("  " + v)
        return 1
    print(f"断言强度门禁通过: 扫描 {len(files)} 文件, 0 个仅弱断言测试")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
