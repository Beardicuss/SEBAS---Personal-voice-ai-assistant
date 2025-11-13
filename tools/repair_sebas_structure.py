import os
import re
import shutil
from pathlib import Path

# --- CONFIG ---
OLD_NAME = "SEBAS - Personal Voice AI Assistant"
NEW_NAME = "sebas"
PACKAGE_ROOT = Path(__file__).parent / NEW_NAME

# --- 1. Rename root folder if necessary ---
old_path = Path(__file__).parent / OLD_NAME
if old_path.exists() and not PACKAGE_ROOT.exists():
    print(f"[+] Renaming root folder: {OLD_NAME} -> {NEW_NAME}")
    shutil.move(str(old_path), str(PACKAGE_ROOT))
elif not PACKAGE_ROOT.exists():
    print(f"[!] Could not find {OLD_NAME}. Ensure script is in the correct directory.")
else:
    print("[=] Package folder already correctly named 'sebas'")

# --- 2. Ensure __init__.py exists in all relevant subfolders ---
target_dirs = [
    PACKAGE_ROOT,
    PACKAGE_ROOT / "api",
    PACKAGE_ROOT / "skills",
    PACKAGE_ROOT / "services",
    PACKAGE_ROOT / "integrations",
    PACKAGE_ROOT / "logging_conf",
    PACKAGE_ROOT / "ui",
]
for d in target_dirs:
    d.mkdir(parents=True, exist_ok=True)
    init_file = d / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# auto-created for Python package recognition\n", encoding="utf-8")
        print(f"[+] Created {init_file.relative_to(Path(__file__).parent)}")

# --- 3. Rewrite imports to absolute (from sebas.XXX) ---
pattern = re.compile(r"^(from\s+)([A-Za-z0-9_]+)(\s+import\s+.+)$")
for pyfile in PACKAGE_ROOT.rglob("*.py"):
    text = pyfile.read_text(encoding="utf-8", errors="ignore")
    changed = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = pattern.match(line.strip())
        if m and not m.group(2).startswith("sebas"):
            # Only rewrite if not already absolute
            new_line = f"{m.group(1)}sebas.{m.group(2)}{m.group(3)}"
            lines[i] = new_line
            changed.append((i + 1, line.strip(), new_line))
    if changed:
        pyfile.write_text("\n".join(lines), encoding="utf-8")
        print(f"[~] Updated imports in {pyfile.name}: {len(changed)} lines modified")

# --- 4. Add .vscode/settings.json configuration for analysis ---
vscode_dir = Path(__file__).parent / ".vscode"
vscode_dir.mkdir(exist_ok=True)
settings_path = vscode_dir / "settings.json"
settings_json = """{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/sebas"
  ],
  "python.defaultInterpreterPath": "venv/Scripts/python.exe"
}
"""
if not settings_path.exists():
    settings_path.write_text(settings_json, encoding="utf-8")
    print("[+] Created VS Code settings.json")

# --- 5. Summary ---
print("\n✅ SEBAS project structure repaired.")
print("Now open VS Code, reload the window, and run:")
print("    python -m sebas.main")
print("\nYour imports and packages should now resolve cleanly.")
