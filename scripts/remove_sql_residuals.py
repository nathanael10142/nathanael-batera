"""
Script safe-cleaner to remove residual SQL/SQLAlchemy legacy code from the repository.

Usage (dry-run):
    python remove_sql_residuals.py --dry-run

To actually delete pass --confirm
    python remove_sql_residuals.py --confirm

This script is explicit and requires confirmation to avoid accidental deletions.
It will target known legacy SQL locations only. It will not touch the main
`app/` code using Firestore unless explicitly matched in the `TARGETS` list.
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "legacy_sql_backup",
    ROOT / "app" / "models" / "sql_models.py",
    ROOT / "alembic",
    ROOT / "alembic.ini",
]


def human_size(p: Path) -> str:
    try:
        if p.is_file():
            return f"{p.stat().st_size} bytes"
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return f"{size} bytes"
    except Exception:
        return "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually delete the targets")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    to_delete = [p for p in TARGETS if p.exists()]

    if not to_delete:
        print("No legacy SQL targets found. Nothing to do.")
        return

    print("Found the following legacy SQL targets:")
    for p in to_delete:
        print(f" - {p} ({human_size(p)})")

    if args.dry_run or not args.confirm:
        print("\nDry run mode. No files will be deleted. Use --confirm to delete.")
        return

    # Confirm again interactively
    resp = input("Type 'DELETE' to permanently remove these files: ")
    if resp != "DELETE":
        print("Confirmation mismatch. Aborting.")
        return

    # Perform deletion
    for p in to_delete:
        try:
            if p.is_dir():
                shutil.rmtree(p)
                print(f"Removed directory: {p}")
            else:
                p.unlink()
                print(f"Removed file: {p}")
        except Exception as e:
            print(f"Failed to remove {p}: {e}")

    print("Cleanup complete.")


if __name__ == "__main__":
    main()
