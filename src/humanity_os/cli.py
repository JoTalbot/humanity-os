"""Command-line entry point; intentionally loopback-only until authentication exists."""
import argparse
import os
from pathlib import Path

from humanity_os.store import KnowledgeStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="humanity-os")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--backup-to",
        metavar="PATH",
        help="create a consistent, non-overwriting SQLite backup and exit",
    )
    parser.add_argument(
        "--verify-backup",
        metavar="PATH",
        help="verify a SQLite backup and print its record count",
    )
    args = parser.parse_args()

    database_path = os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    if args.backup_to and args.verify_backup:
        parser.error("--backup-to and --verify-backup cannot be used together")
    if args.backup_to:
        result = KnowledgeStore(database_path).backup(args.backup_to)
        print(f"Backup created: {result}")
        return
    if args.verify_backup:
        count = KnowledgeStore.verify_backup(args.verify_backup)
        print(f"Backup verified: {count} knowledge records")
        return

    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("The 0.1 API has no authentication; only loopback binding is allowed.")
    import uvicorn

    uvicorn.run("humanity_os.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
