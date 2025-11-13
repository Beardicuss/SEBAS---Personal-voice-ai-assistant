"""
SEBAS Structure Repair v2
Works from ANY location. Autodetects project structure.
"""

import os
import sys
from sebas.pathlib import Path

print("\n========== SEBAS STRUCTURE REPAIR ==========\n")

# ---------------------------------------
# 1. Определение корня проекта
# ---------------------------------------

def find_project_root(start: Path) -> Path | None:
    """
    Ищем папку sebas в текущей директории.
    Если найдено: возвращаем текущую директорию как корень проекта.
    """
    for p in start.iterdir():
        if p.is_dir() and p.name.lower() == "sebas":
            return start
    return None


# Точка запуска скрипта
start_dir = Path.cwd()
root = find_project_root(start_dir)

if root is None:
    print("[❌] ERROR: Can't find 'sebas' folder in:")
    print(f"    {start_dir}")
    print("    Run script from directory containing 'sebas'.")
    sys.exit(1)

print(f"[✔] Project root detected: {root}")

PACKAGE = root / "sebas"

# ---------------------------------------
# 2. Обязательные подпапки
# ---------------------------------------
mandatory_dirs = [
    PACKAGE,
    PACKAGE / "api",
    PACKAGE / "services",
    PACKAGE / "skills",
    PACKAGE / "integrations",
    PACKAGE / "constants",
    PACKAGE / "permissions",
    PACKAGE / "nlp",
    PACKAGE / "wakeword",
    PACKAGE / "ui",
    PACKAGE / "logging_conf",
    PACKAGE / "tools",
]

print("\n[+] Ensuring project directories...")

for d in mandatory_dirs:
    d.mkdir(parents=True, exist_ok=True)
    init_file = d / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# auto-generated\n", encoding="utf-8")
        print(f"    Created {init_file}")


# ---------------------------------------
# 3. FIX imports → absolute sebas.xxx
# ---------------------------------------
import_rewrites = 0

print("\n[+] Rewriting imports to absolute form (from sebas.xxx)...")

for py in PACKAGE.rglob("*.py"):
    text = py.read_text(encoding="utf-8", errors="ignore").splitlines()
    new_lines = []
    modified = False

    for line in text:
        stripped = line.strip()

        # from X import Y → from sebas.X import Y
        if stripped.startswith("from ") and " import " in stripped:
            parts = stripped.split()
            module = parts[1]

            # Skip if already absolute or external module
            if not module.startswith("sebas") and "." not in module:
                line = line.replace(f"from {module} ", f"from sebas.{module} ")
                modified = True
                import_rewrites += 1

        new_lines.append(line)

    if modified:
        py.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"    Updated imports in: {py.name}")

print(f"[✔] Imports rewritten: {import_rewrites} modifications")


# ---------------------------------------
# 4. VSCode setup
# ---------------------------------------
vscode = root / ".vscode"
vscode.mkdir(exist_ok=True)
settings = vscode / "settings.json"

settings.write_text(
    """{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/sebas"
  ],
  "python.defaultInterpreterPath": "venv_sebas/Scripts/python.exe"
}
""",
    encoding="utf-8"
)

print("\n[✔] VSCode settings applied")


# ---------------------------------------
# DONE
# ---------------------------------------
print("\n✅ SEBAS structure repaired successfully!")
print("Restart VSCode for paths to refresh.")