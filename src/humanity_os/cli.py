"""Command-line entry point; intentionally loopback-only until security review."""
import argparse
import getpass
import json
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
    operations.add_argument("--restore-from", metavar="PATH", help="restore a verified SQLite backup")
    operations.add_argument("--import-workspace-from", metavar="PATH", help="replace workspace from a verified portable JSON export")
    operations.add_argument("--generate-api-token", action="store_true", help="generate a 256-bit bearer token")
    operations.add_argument("--set-owner-password", action="store_true", help="set or rotate the local owner password")
    operations.add_argument("--export-workspace", metavar="PATH", help="write a portable workspace export")
    operations.add_argument("--delete-workspace", action="store_true", help="irreversibly delete the local workspace after a safety backup")
    parser.add_argument("--safety-backup", metavar="PATH")
    parser.add_argument("--confirm-restore", action="store_true")
    parser.add_argument("--confirm-delete", action="store_true")
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

    if args.safety_backup and not (args.restore_from or args.import_workspace_from or args.delete_workspace):
        parser.error("--safety-backup is only valid with restore, import or deletion")
    if (args.restore_from or args.import_workspace_from) and not args.safety_backup:
        parser.error("Restore/import requires --safety-backup")
    if (args.restore_from or args.import_workspace_from) and not args.confirm_restore:
        parser.error("Restore/import requires --confirm-restore")
    if args.confirm_restore and not (args.restore_from or args.import_workspace_from):
        parser.error("--confirm-restore is only valid with restore/import")
    if args.delete_workspace and not args.safety_backup:
        parser.error("--delete-workspace requires --safety-backup")
    if args.delete_workspace and not args.confirm_delete:
        parser.error("--delete-workspace requires --confirm-delete")
    if args.confirm_delete and not args.delete_workspace:
        parser.error("--confirm-delete is only valid with --delete-workspace")

    if args.backup_to:
        print(f"Backup created: {KnowledgeStore(database_path).backup(args.backup_to)}")
        return
    if args.verify_backup:
        print(f"Backup verified: {KnowledgeStore.verify_backup(args.verify_backup)} knowledge records")
        return
    if args.export_workspace:
        document = KnowledgeStore(database_path).export_workspace()
        target = Path(args.export_workspace).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(document, output, ensure_ascii=False, indent=2)
            output.write("\n")
        print(f"Workspace export created: {target}")
        print(f"SHA-256: {document['integrity']['canonical_document_sha256']}")
        return
    if args.delete_workspace:
        database = Path(database_path).expanduser()
        if database_path == ":memory:":
            parser.error("Workspace deletion requires a file-backed database")
        if not database.exists():
            parser.error("Workspace database does not exist")
        if database.is_symlink():
            parser.error("Refusing to delete a database symlink")
        protected_paths = {
            database.resolve(),
            Path(str(database) + "-wal").resolve(),
            Path(str(database) + "-shm").resolve(),
        }
        if Path(args.safety_backup).expanduser().resolve() in protected_paths:
            parser.error("Safety backup must differ from the active database and SQLite sidecars")
        # This command is intentionally offline: stop the server before running it.
        backup = KnowledgeStore(database_path).backup(args.safety_backup)
        KnowledgeStore.verify_backup(backup)
        KnowledgeStore.checkpoint_database(database)
        for suffix in ("", "-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        print(f"Workspace database and SQLite sidecars deleted: {database}")
        print(f"Verified safety backup retained at: {backup}")
        print("Copies in other backups, snapshots, or filesystems are not erased.")
        return
    if args.import_workspace_from:
        count = KnowledgeStore(database_path).import_workspace(
            args.import_workspace_from, args.safety_backup
        )
        print(f"Portable workspace imported: {count} knowledge records")
        print(f"Pre-import safety backup: {args.safety_backup}")
        print("Owner password and active sessions were not imported; configure a new owner password.")
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
