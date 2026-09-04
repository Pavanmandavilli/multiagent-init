from __future__ import annotations

import sys

from .generator import generate_project
from .wizard import run_wizard


def main() -> int:
    try:
        config = run_wizard()
        destination = generate_project(config)

        print()
        print("🎉 Done!")
        print()
        print("Next steps:")
        print()
        print(f"  cd {destination.name}")
        print("  python3 -m venv .venv")
        print("  source .venv/bin/activate  # macOS/Linux")
        print("  pip install .")
        print("  python main.py")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return 130

    except (ValueError, FileExistsError, OSError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
