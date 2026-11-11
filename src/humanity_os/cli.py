"""Command-line entry point; intentionally loopback-only until authentication exists."""
import argparse
import os
from pathlib import Path

from humanity_os.store import KnowledgeStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="humanity-os")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument(
        "--backup-to",
        metavar="PATH",
        help="create a consistent, non-overwriting SQLite backup and exit",
    )
    operations.add_argument(
        "--verify-backup",
        metavar="PATH",
        help="verify a SQLite backup and print its record count",
    )
    operations.add_argument(
        "--restore-from",
        metavar="PATH",
        help="restore from a verified backup after creating a safety snapshot",
    )
    parser.add_argument(
        "--safety-backup",
        metavar="PATH",
        help="new, non-existing path for the mandatory pre-restore snapshot",
    )
    args = parser.parse_args()

    database_path = os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    if args.safety_backup and not args.restore_from:
        parser.error("--safety-backup is only valid with --restore-from")
    if args.restore_from and not args.safety_backup:
        parser.error("--restore-from requires --safety-backup")

    if args.backup_to:
        result = KnowledgeStore(database_path).backup(args.backup_to)
        print(f"Backup created: {result}")
        return
    if args.verify_backup:
        count = KnowledgeStore.verify_backup(args.verify_backup)
        print(f"Backup verified: {count} knowledge records")
        return
    if args.restore_from:
        store = KnowledgeStore(database_path)
        count = store.restore(args.restore_from, args.safety_backup)
        print(f"Restore completed: {count} knowledge records")
        print(f"Pre-restore safety backup: {args.safety_backup}")
        return

    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("The 0.1 API has no authentication; only loopback binding is allowed.")
    import uvicorn

    uvicorn.run("humanity_os.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
