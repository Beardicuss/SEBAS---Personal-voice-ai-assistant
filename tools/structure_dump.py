"""
SEBAS PROJECT STRUCTURE DUMP TOOL
Generates a full tree of the current project structure
and saves it to tools/logs/project_structure.txt

Run:
    python -m sebas.tools.structure_dump
"""

import os
from pathlib import Path
from datetime import datetime

# Detect project root automatically
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "tools" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = LOG_DIR / "project_structure.txt"


def tree(dir_path: Path, prefix: str = "") -> str:
    """Generate ASCII tree structure for given folder."""
    entries = sorted(os.listdir(dir_path))
    result = ""

    pointers = {
        "tee": "├── ",
        "last": "└── ",
        "pipe": "│   ",
        "space": "    ",
    }

    for index, name in enumerate(entries):
        full = dir_path / name
        connector = (
            pointers["last"] if index == len(entries) - 1 else pointers["tee"]
        )

        result += prefix + connector + name + "\n"

        if full.is_dir():
            extension = (
                pointers["space"]
                if index == len(entries) - 1
                else pointers["pipe"]
            )
            result += tree(full, prefix + extension)

    return result


def generate_structure():
    """Generate and save full project structure into a log file."""
    header = (
        "=============================================\n"
        "         SEBAS PROJECT STRUCTURE Mk.I\n"
        "=============================================\n"
        f"Generated: {datetime.now().isoformat()}\n\n"
    )

    structure = header
    structure += tree(ROOT)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        f.write(structure)

    print("[✔] Project structure saved to:")
    print(f"    {OUT_PATH}")


if __name__ == "__main__":
    generate_structure()
