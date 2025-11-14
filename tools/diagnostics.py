"""
SEBAS DIAGNOSTICS SUITE Mk.IV — SOFTCURSE EDITION

Features included:
    Mk.I   – Detect unused modules, circular imports,
             dangerous calls, missing __init__.py
    Mk.II  – Function performance analyzer
    Mk.III – Static architecture mini-AI analysis
    Mk.IV  – Combined report, unified structure,
             sarcasm not included (but present spiritually)

Run with:
    python -m sebas.tools.diagnostics
"""

import ast
import os
import timeit
from pathlib import Path
from datetime import datetime


# ============================================================
# SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "tools" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "diagnostics_report.txt"


# ============================================================
# Utility: Get list of Python files
# ============================================================

def find_py_files():
    return [
        p for p in PROJECT_ROOT.rglob("*.py")
        if "tools" not in p.parts  # skip diagnostics scripts themselves
    ]


# ============================================================
# Mk.I — UNUSED MODULE DETECTOR
# ============================================================

def detect_unused(py_files):
    imports = set()
    modules = {f.stem for f in py_files}

    for f in py_files:
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

    unused = modules - imports
    unused = {
        u for u in unused
        if u not in ("__init__", "diagnostics", "repair_sebas_structure")
    }
    return sorted(list(unused))


# ============================================================
# Mk.I — CIRCULAR IMPORT DETECTOR
# ============================================================

def parse_imports(file: Path):
    try:
        tree = ast.parse(file.read_text(errors="ignore"))
    except Exception:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


def build_graph(py_files):
    graph = {}
    for f in py_files:
        graph[f.stem] = parse_imports(f)
    return graph


def detect_cycles(graph):
    visited = set()
    stack = set()
    cycles = []

    def dfs(node, path):
        visited.add(node)
        stack.add(node)

        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if dep not in visited:
                dfs(dep, path + [dep])
            elif dep in stack:
                try:
                    start = path.index(dep)
                    cycles.append(path[start:] + [dep])
                except ValueError:
                    pass

        stack.remove(node)

    for mod in graph:
        if mod not in visited:
            dfs(mod, [mod])

    return cycles


# ============================================================
# Mk.I — DANGEROUS CALLS DETECTOR
# ============================================================

DANGEROUS = ("eval", "exec", "os.system", "subprocess.Popen", "open('/etc/passwd'")

def detect_dangerous_calls(py_files):
    result = []
    for f in py_files:
        code = f.read_text(errors="ignore")
        for d in DANGEROUS:
            if d in code:
                result.append((f, d))
    return result


# ============================================================
# Mk.I — MISSING __init__.py
# ============================================================

def detect_missing_inits():
    missing = []
    for d in PROJECT_ROOT.rglob("*"):
        if not d.is_dir():
            continue
        if "tools" in d.parts:
            continue

        if any(p.suffix == ".py" for p in d.glob("*")):
            init = d / "__init__.py"
            if not init.exists():
                missing.append(str(d))
    return missing


# ============================================================
# Mk.II — FUNCTION SPEED ANALYZER
# ============================================================

def analyze_function_speed(py_files):
    results = []

    for file in py_files:
        code = file.read_text(errors="ignore")

        try:
            tree = ast.parse(code)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name

                # skip private functions
                if name.startswith("_"):
                    continue

                # extract source
                source = ast.get_source_segment(code, node)
                if not source:
                    continue

                test_stmt = f"{name}()"

                try:
                    t = timeit.timeit(
                        stmt=test_stmt,
                        setup=source,
                        number=5
                    ) / 5
                except Exception:
                    continue

                results.append({
                    "file": str(file),
                    "function": name,
                    "time_ms": round(t * 1000, 3),
                })

    return results


# ============================================================
# Mk.III — MINI AI ARCHITECTURE REVIEW
# ============================================================

def mini_ai_architecture_review(py_files):
    issues = []

    for file in py_files:
        try:
            code = file.read_text(errors="ignore")
        except Exception:
            continue

        lines = code.count("\n")
        if lines > 800:
            issues.append((file, "File extremely large (>800 lines). Consider refactoring."))

        try:
            tree = ast.parse(code)
        except Exception:
            continue

        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

        if len(classes) > 5:
            issues.append((file, f"Too many classes ({len(classes)}). Module overloaded."))

        if len(funcs) > 50:
            issues.append((file, f"Too many functions ({len(funcs)}). Logical separation needed."))

        for c in classes:
            methods = [m for m in c.body if isinstance(m, ast.FunctionDef)]
            if len(methods) > 15:
                issues.append((file, f"God-object detected: class {c.name} has {len(methods)} methods."))

    return issues


# ============================================================
# Write full report (Mk.IV)
# ============================================================

def write_report(unused, cycles, dangerous, missing_init, speed, arch):
    with open(LOG_PATH, "w", encoding="utf-8") as log:
        log.write("===== SEBAS DIAGNOSTICS SUITE Mk.IV OMEGA =====\n")
        log.write(f"Generated: {datetime.now().isoformat()}\n\n")

        # Unused modules
        log.write("=== 1. UNUSED MODULES ===\n")
        if unused:
            for u in unused:
                log.write(f" • {u}\n")
        else:
            log.write("No unused modules.\n")
        log.write("\n")

        # Cycles
        log.write("=== 2. CIRCULAR IMPORTS ===\n")
        if cycles:
            for c in cycles:
                log.write("CYCLE:\n")
                for i in range(len(c)-1):
                    log.write(f"  {c[i]} → {c[i+1]}\n")
                log.write("\n")
        else:
            log.write("No circular imports.\n")
        log.write("\n")

        # Dangerous calls
        log.write("=== 3. DANGEROUS CALLS ===\n")
        if dangerous:
            for f, d in dangerous:
                log.write(f" • {f} uses {d}\n")
        else:
            log.write("None detected.\n")
        log.write("\n")

        # Missing __init__
        log.write("=== 4. MISSING __init__.py ===\n")
        if missing_init:
            for m in missing_init:
                log.write(f" • {m}\n")
        else:
            log.write("No missing __init__.\n")
        log.write("\n")

        # Function speed
        log.write("=== 5. FUNCTION SPEED (Mk.II) ===\n")
        slow = [r for r in speed if r["time_ms"] > 2]
        if slow:
            for r in slow:
                log.write(f" • {r['function']}() in {r['file']} is slow: {r['time_ms']} ms\n")
        else:
            log.write("No slow functions detected.\n")
        log.write("\n")

        # Architecture review
        log.write("=== 6. MINI AI ARCHITECTURE REVIEW (Mk.III) ===\n")
        if arch:
            for f, msg in arch:
                log.write(f" • {f}: {msg}\n")
        else:
            log.write("Architecture looks clean.\n")
        log.write("\n")

    print(f"\n[✔] Diagnostics complete!\nReport saved at:\n{LOG_PATH}\n")


# ============================================================
# MAIN
# ============================================================

def main():
    py_files = find_py_files()

    unused = detect_unused(py_files)
    graph = build_graph(py_files)
    cycles = detect_cycles(graph)
    dangerous = detect_dangerous_calls(py_files)
    missing_init = detect_missing_inits()
    speed = analyze_function_speed(py_files)
    arch = mini_ai_architecture_review(py_files)

    write_report(unused, cycles, dangerous, missing_init, speed, arch)


if __name__ == "__main__":
    main()
