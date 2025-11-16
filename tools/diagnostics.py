"""
SEBAS DIAGNOSTICS SUITE Mk.V — FIXED & IMPROVED

Fixes:
- Accurate unused module detection
- Removed broken function speed analyzer
- Improved dangerous call detection
- Better error handling
- More accurate reporting

Run with:
    python -m sebas.tools.diagnostics
"""

import ast
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ============================================================
# SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "tools" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "diagnostics_report.txt"

# Files/modules to always exclude
EXCLUDE_FILES = {"__init__", "diagnostics", "repair_sebas_structure", "structure_dump"}
EXCLUDE_DIRS = {"__pycache__", ".git", ".vs", "venv", "venv_sebas"}


# ============================================================
# Utility: Get list of Python files
# ============================================================

def find_py_files():
    files = []
    for p in PROJECT_ROOT.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in p.parts for excluded in EXCLUDE_DIRS):
            continue
        # Skip tools directory
        if "tools" in p.parts:
            continue
        files.append(p)
    return files


# ============================================================
# IMPROVED: Unused Module Detector
# ============================================================

def detect_unused(py_files):
    """
    Detect modules that are defined but never imported.
    Accounts for various import styles.
    """
    # Get all module names (files)
    all_modules = {f.stem for f in py_files if f.stem not in EXCLUDE_FILES}
    
    # Track all imports
    imported_modules = set()
    
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except Exception:
            continue

        for node in ast.walk(tree):
            # Direct import: import foo
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    # Add all parts (sebas.skills.base_skill -> add base_skill)
                    imported_modules.update(parts)
            
            # From import: from sebas.skills import base_skill
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    parts = node.module.split(".")
                    imported_modules.update(parts)
                # Also add imported names
                for alias in node.names:
                    imported_modules.add(alias.name)
    
    # Calculate unused (modules never imported)
    unused = all_modules - imported_modules
    
    # Filter out common files that might not be imported directly
    common_entry_points = {"main", "run", "setup", "config", "app"}
    unused = {u for u in unused if u not in common_entry_points}
    
    return sorted(list(unused))


# ============================================================
# IMPROVED: Circular Import Detector
# ============================================================

def parse_imports(file: Path):
    """Extract all module imports from a file."""
    try:
        tree = ast.parse(file.read_text(errors="ignore"))
    except Exception:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                # Get the first part of the import
                module = n.name.split(".")[0]
                imports.append(module)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                imports.append(module)
    
    return list(set(imports))  # Deduplicate


def build_graph(py_files):
    """Build dependency graph."""
    graph = {}
    for f in py_files:
        if f.stem not in EXCLUDE_FILES:
            graph[f.stem] = parse_imports(f)
    return graph


def detect_cycles(graph):
    """Detect circular dependencies using DFS."""
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)

        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            
            if dep not in visited:
                dfs(dep, path + [dep])
            elif dep in rec_stack:
                # Found a cycle
                try:
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    if cycle not in cycles:
                        cycles.append(cycle)
                except ValueError:
                    pass

        rec_stack.remove(node)

    for mod in graph:
        if mod not in visited:
            dfs(mod, [mod])

    return cycles


# ============================================================
# IMPROVED: Dangerous Calls Detector
# ============================================================

def detect_dangerous_calls(py_files):
    """
    Detect potentially dangerous function calls.
    More accurate - only flags actual calls, not strings/comments.
    """
    dangerous_patterns = {
        'eval': r'\beval\s*\(',
        'exec': r'\bexec\s*\(',
        'os.system': r'os\.system\s*\(',
        '__import__': r'\b__import__\s*\(',
        'compile': r'\bcompile\s*\(',
    }
    
    results = []
    
    for f in py_files:
        content = f.read_text(errors="ignore")
        
        # Remove comments and strings to avoid false positives
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check function name
                    func_name = None
                    
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        # For os.system, subprocess.call, etc.
                        if isinstance(node.func.value, ast.Name):
                            func_name = f"{node.func.value.id}.{node.func.attr}"
                    
                    # Check against dangerous patterns
                    if func_name:
                        if func_name in ['eval', 'exec', '__import__', 'compile']:
                            results.append((f, func_name))
                        elif func_name in ['os.system', 'subprocess.call', 'subprocess.Popen']:
                            results.append((f, func_name))
        
        except Exception:
            # Fallback to regex if AST parsing fails
            for name, pattern in dangerous_patterns.items():
                if re.search(pattern, content):
                    results.append((f, name))
                    break
    
    return results


# ============================================================
# IMPROVED: Missing __init__.py Detector
# ============================================================

def detect_missing_inits():
    """Find Python package directories missing __init__.py"""
    missing = []
    
    for d in PROJECT_ROOT.rglob("*"):
        if not d.is_dir():
            continue
        
        # Skip excluded directories
        if any(excluded in d.parts for excluded in EXCLUDE_DIRS):
            continue
        if "tools" in d.parts:
            continue

        # Check if directory contains Python files
        py_files = list(d.glob("*.py"))
        if py_files:
            init_file = d / "__init__.py"
            if not init_file.exists():
                missing.append(str(d.relative_to(PROJECT_ROOT)))
    
    return missing


# ============================================================
# NEW: Code Quality Metrics
# ============================================================

def analyze_code_quality(py_files):
    """Analyze code quality metrics."""
    metrics = {
        'total_files': len(py_files),
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0,
        'large_files': [],
        'complex_functions': [],
        'god_objects': []
    }
    
    for file in py_files:
        try:
            content = file.read_text(errors="ignore")
            lines = content.count('\n')
            metrics['total_lines'] += lines
            
            if lines > 500:
                metrics['large_files'].append((file, lines))
            
            try:
                tree = ast.parse(content)
                
                # Count functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        metrics['total_functions'] += 1
                        
                        # Check function complexity (lines)
                        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                            if node.end_lineno is not None and node.lineno is not None:
                                func_lines = node.end_lineno - node.lineno
                                if func_lines > 100:
                                    metrics['complex_functions'].append((file, node.name, func_lines))
                    
                    elif isinstance(node, ast.ClassDef):
                        metrics['total_classes'] += 1
                        
                        # Check for god objects (too many methods)
                        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        if len(methods) > 20:
                            metrics['god_objects'].append((file, node.name, len(methods)))
            
            except Exception:
                pass
        
        except Exception:
            continue
    
    return metrics


# ============================================================
# NEW: Dependency Analysis
# ============================================================

def analyze_dependencies(py_files):
    """Analyze external dependencies."""
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'logging', 'threading',
        'collections', 'functools', 're', 'pathlib', 'typing', 'enum',
        'dataclasses', 'subprocess', 'socket', 'platform', 'shutil', 'tempfile'
    }
    
    external_deps = set()
    
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        if module not in stdlib_modules and module != 'sebas':
                            external_deps.add(module)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        if module not in stdlib_modules and module != 'sebas':
                            external_deps.add(module)
        
        except Exception:
            continue
    
    return sorted(list(external_deps))


# ============================================================
# Write Report
# ============================================================

def write_report(unused, cycles, dangerous, missing_init, quality, dependencies):
    """Generate comprehensive diagnostics report."""
    with open(LOG_PATH, "w", encoding="utf-8") as log:
        log.write("=" * 60 + "\n")
        log.write("SEBAS DIAGNOSTICS SUITE Mk.V — COMPREHENSIVE ANALYSIS\n")
        log.write("=" * 60 + "\n")
        log.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # === SUMMARY ===
        log.write("=" * 60 + "\n")
        log.write("EXECUTIVE SUMMARY\n")
        log.write("=" * 60 + "\n")
        log.write(f"Total Files Analyzed: {quality['total_files']}\n")
        log.write(f"Total Lines of Code: {quality['total_lines']:,}\n")
        log.write(f"Total Functions: {quality['total_functions']}\n")
        log.write(f"Total Classes: {quality['total_classes']}\n")
        log.write(f"Unused Modules: {len(unused)}\n")
        log.write(f"Circular Imports: {len(cycles)}\n")
        log.write(f"Dangerous Calls: {len(dangerous)}\n")
        log.write(f"Missing __init__.py: {len(missing_init)}\n")
        log.write(f"External Dependencies: {len(dependencies)}\n\n")

        # === UNUSED MODULES ===
        log.write("=" * 60 + "\n")
        log.write("1. UNUSED MODULES\n")
        log.write("=" * 60 + "\n")
        if unused:
            log.write(f"Found {len(unused)} potentially unused modules:\n\n")
            for u in unused:
                log.write(f"  • {u}\n")
        else:
            log.write("✓ No unused modules detected.\n")
        log.write("\n")

        # === CIRCULAR IMPORTS ===
        log.write("=" * 60 + "\n")
        log.write("2. CIRCULAR IMPORT DEPENDENCIES\n")
        log.write("=" * 60 + "\n")
        if cycles:
            log.write(f"⚠ Found {len(cycles)} circular dependency chain(s):\n\n")
            for idx, cycle in enumerate(cycles, 1):
                log.write(f"Cycle #{idx}:\n")
                for i in range(len(cycle) - 1):
                    log.write(f"  {cycle[i]} → {cycle[i+1]}\n")
                log.write("\n")
        else:
            log.write("✓ No circular imports detected.\n")
        log.write("\n")

        # === DANGEROUS CALLS ===
        log.write("=" * 60 + "\n")
        log.write("3. POTENTIALLY DANGEROUS CALLS\n")
        log.write("=" * 60 + "\n")
        if dangerous:
            log.write(f"⚠ Found {len(dangerous)} potentially dangerous call(s):\n\n")
            # Group by file
            by_file = defaultdict(list)
            for f, call in dangerous:
                by_file[f].append(call)
            
            for f, calls in by_file.items():
                log.write(f"  {f.relative_to(PROJECT_ROOT)}:\n")
                for call in set(calls):
                    log.write(f"    • {call}\n")
                log.write("\n")
        else:
            log.write("✓ No dangerous calls detected.\n")
        log.write("\n")

        # === MISSING __init__.py ===
        log.write("=" * 60 + "\n")
        log.write("4. MISSING __init__.py FILES\n")
        log.write("=" * 60 + "\n")
        if missing_init:
            log.write(f"⚠ Found {len(missing_init)} director(y/ies) missing __init__.py:\n\n")
            for m in missing_init:
                log.write(f"  • {m}\n")
        else:
            log.write("✓ All Python packages have __init__.py files.\n")
        log.write("\n")

        # === CODE QUALITY ===
        log.write("=" * 60 + "\n")
        log.write("5. CODE QUALITY ANALYSIS\n")
        log.write("=" * 60 + "\n")
        
        # Large files
        if quality['large_files']:
            log.write(f"⚠ Large files (>500 lines):\n\n")
            for f, lines in sorted(quality['large_files'], key=lambda x: x[1], reverse=True)[:10]:
                log.write(f"  • {f.relative_to(PROJECT_ROOT)}: {lines} lines\n")
            log.write("\n")
        
        # Complex functions
        if quality['complex_functions']:
            log.write(f"⚠ Complex functions (>100 lines):\n\n")
            for f, name, lines in sorted(quality['complex_functions'], key=lambda x: x[2], reverse=True)[:10]:
                log.write(f"  • {name}() in {f.relative_to(PROJECT_ROOT)}: {lines} lines\n")
            log.write("\n")
        
        # God objects
        if quality['god_objects']:
            log.write(f"⚠ God objects (>20 methods):\n\n")
            for f, name, methods in sorted(quality['god_objects'], key=lambda x: x[2], reverse=True):
                log.write(f"  • class {name} in {f.relative_to(PROJECT_ROOT)}: {methods} methods\n")
            log.write("\n")
        
        if not (quality['large_files'] or quality['complex_functions'] or quality['god_objects']):
            log.write("✓ Code quality metrics are within acceptable ranges.\n\n")

        # === DEPENDENCIES ===
        log.write("=" * 60 + "\n")
        log.write("6. EXTERNAL DEPENDENCIES\n")
        log.write("=" * 60 + "\n")
        if dependencies:
            log.write(f"Found {len(dependencies)} external package(s):\n\n")
            for dep in dependencies:
                log.write(f"  • {dep}\n")
        else:
            log.write("✓ No external dependencies detected (stdlib only).\n")
        log.write("\n")

        # === RECOMMENDATIONS ===
        log.write("=" * 60 + "\n")
        log.write("7. RECOMMENDATIONS\n")
        log.write("=" * 60 + "\n")
        
        recommendations = []
        
        if len(unused) > 20:
            recommendations.append("• Consider removing unused modules to reduce complexity")
        
        if cycles:
            recommendations.append("• Refactor circular imports to improve modularity")
        
        if dangerous:
            recommendations.append("• Review dangerous calls (eval, exec) for security risks")
        
        if missing_init:
            recommendations.append("• Add __init__.py files to all package directories")
        
        if quality['large_files']:
            recommendations.append("• Split large files (>500 lines) into smaller modules")
        
        if quality['god_objects']:
            recommendations.append("• Refactor god objects (>20 methods) into smaller classes")
        
        if recommendations:
            for rec in recommendations:
                log.write(f"{rec}\n")
        else:
            log.write("✓ No critical issues found. Code structure looks good!\n")
        
        log.write("\n")
        log.write("=" * 60 + "\n")
        log.write("END OF REPORT\n")
        log.write("=" * 60 + "\n")

    print(f"\n{'=' * 60}")
    print("✓ Diagnostics Complete!")
    print(f"{'=' * 60}")
    print(f"Report saved to: {LOG_PATH}")
    print(f"\nSummary:")
    print(f"  Files analyzed: {quality['total_files']}")
    print(f"  Lines of code: {quality['total_lines']:,}")
    print(f"  Issues found: {len(unused) + len(cycles) + len(dangerous) + len(missing_init)}")
    print(f"{'=' * 60}\n")


# ============================================================
# MAIN
# ============================================================

def main():
    """Run all diagnostics."""
    print("\n" + "=" * 60)
    print("SEBAS DIAGNOSTICS SUITE Mk.V")
    print("=" * 60 + "\n")
    
    print("Scanning project files...")
    py_files = find_py_files()
    print(f"Found {len(py_files)} Python files\n")
    
    print("Analyzing unused modules...")
    unused = detect_unused(py_files)
    
    print("Building dependency graph...")
    graph = build_graph(py_files)
    
    print("Detecting circular imports...")
    cycles = detect_cycles(graph)
    
    print("Scanning for dangerous calls...")
    dangerous = detect_dangerous_calls(py_files)
    
    print("Checking for missing __init__.py...")
    missing_init = detect_missing_inits()
    
    print("Analyzing code quality...")
    quality = analyze_code_quality(py_files)
    
    print("Analyzing dependencies...")
    dependencies = analyze_dependencies(py_files)
    
    print("Generating report...\n")
    write_report(unused, cycles, dangerous, missing_init, quality, dependencies)


if __name__ == "__main__":
    main()