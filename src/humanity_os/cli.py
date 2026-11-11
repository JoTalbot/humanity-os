"""Command-line entry point; intentionally loopback-only until security review."""
import argparse
import getpass
import os
import secrets
from pathlib import Path

from humanity_os.auth import AuthStore
from humanity_os.store import KnowledgeStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="humanity-os")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("--backup-to", metavar="PATH", help="create a consistent SQLite backup")
    operations.add_argument("--verify-backup", metavar="PATH", help="verify a SQLite backup")
    operations.add_argument("--restore-from", metavar="PATH", help="restore a verified backup")
    operations.add_argument("--generate-api-token", action="store_true", help="generate a 256-bit bearer token")
    operations.add_argument("--set-owner-password", action="store_true", help="set or rotate the local owner password")
    parser.add_argument("--safety-backup", metavar="PATH")
    parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()

    if args.generate_api_token:
        print(secrets.token_urlsafe(32))
        return

    database_path = os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    if args.set_owner_password:
        first = getpass.getpass("New owner password (minimum 12 characters): ")
        second = getpass.getpass("Repeat owner password: ")
        if first != second:
            parser.error("Passwords do not match")
        try:
            AuthStore(database_path).set_owner_password(first)
        except ValueError as exc:
            parser.error(str(exc))
        print("Owner password updated; all existing sessions were revoked.")
        return

    if args.safety_backup and not args.restore_from:
        parser.error("--safety-backup is only valid with --restore-from")
    if args.restore_from and not args.safety_backup:
        parser.error("--restore-from requires --safety-backup")
    if args.restore_from and not args.confirm_restore:
        parser.error("--restore-from requires --confirm-restore")
    if args.confirm_restore and not args.restore_from:
        parser.error("--confirm-restore is only valid with --restore-from")

    if args.backup_to:
        print(f"Backup created: {KnowledgeStore(database_path).backup(args.backup_to)}")
        return
    if args.verify_backup:
        print(f"Backup verified: {KnowledgeStore.verify_backup(args.verify_backup)} knowledge records")
        return
    if args.restore_from:
        count = KnowledgeStore(database_path).restore(args.restore_from, args.safety_backup)
        print(f"Restore completed: {count} knowledge records")
        print(f"Pre-restore safety backup: {args.safety_backup}")
        return

    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("The 0.1 API is loopback-only, even when authentication is enabled.")
    import uvicorn

    uvicorn.run("humanity_os.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
