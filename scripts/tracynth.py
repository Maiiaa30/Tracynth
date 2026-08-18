#!/usr/bin/env python3
"""Cross-platform operator commands for a Docker Compose Tracynth deployment.

Passwords and application secrets are never accepted as command-line options.
Account commands delegate to Django's interactive, no-echo prompts.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
from typing import BinaryIO, Sequence


UTILITY_IMAGE = os.getenv("TRACYNTH_UTILITY_IMAGE", "alpine:3.22")
SAFE_DATABASE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


class OpsError(RuntimeError):
    """An expected, safely reportable operator error."""


def command_prefix(compose_file: Path | None) -> list[str]:
    prefix = ["docker", "compose"]
    if compose_file:
        prefix.extend(["--file", str(compose_file)])
    return prefix


def run(
    command: Sequence[str],
    *,
    check: bool = True,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | int | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    print("+ " + " ".join(command), file=sys.stderr)
    return subprocess.run(
        list(command),
        check=check,
        stdin=stdin,
        stdout=subprocess.PIPE if capture else stdout,
        stderr=subprocess.PIPE if capture else None,
        text=capture,
    )


def compose(args: argparse.Namespace, *command: str, **kwargs) -> subprocess.CompletedProcess:
    return run([*command_prefix(args.compose_file), *command], **kwargs)


def validate_compose(args: argparse.Namespace) -> None:
    if shutil.which("docker") is None:
        raise OpsError("Docker is not installed or is not on PATH")
    compose(args, "config", "--quiet")


def compose_config(args: argparse.Namespace) -> dict:
    result = compose(args, "config", "--format", "json", capture=True)
    return json.loads(result.stdout)


def service_environment(args: argparse.Namespace, service: str, name: str) -> str:
    result = compose(args, "exec", "-T", service, "printenv", name, capture=True)
    value = result.stdout.strip()
    if not value:
        raise OpsError(f"{name} is not set in the {service} service")
    return value


def postgres_identity(args: argparse.Namespace) -> tuple[str, str]:
    user = service_environment(args, args.postgres_service, "POSTGRES_USER")
    database = service_environment(args, args.postgres_service, "POSTGRES_DB")
    if not SAFE_DATABASE_NAME.fullmatch(user) or not SAFE_DATABASE_NAME.fullmatch(database):
        raise OpsError("PostgreSQL user/database contains unsupported characters")
    if database == "postgres":
        raise OpsError("refusing to back up or replace the PostgreSQL maintenance database")
    return user, database


def wait_for_postgres(args: argparse.Namespace, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = compose(
            args,
            "exec",
            "-T",
            args.postgres_service,
            "pg_isready",
            "--quiet",
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise OpsError("PostgreSQL did not become ready before the timeout")


def resolved_volume(args: argparse.Namespace, logical_name: str) -> str:
    volume = compose_config(args).get("volumes", {}).get(logical_name)
    if not volume or not volume.get("name"):
        raise OpsError(f"Compose volume {logical_name!r} is not defined")
    return str(volume["name"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utility_container(*arguments: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--read-only",
        "--user=10001:10001",
        *arguments,
    ]


@contextmanager
def paused_stack(args: argparse.Namespace):
    result = compose(
        args, "ps", "--services", "--filter", "status=running", capture=True
    )
    running = [name for name in result.stdout.splitlines() if name]
    paused = [
        name for name in running if name not in {args.postgres_service, args.redis_service}
    ]
    postgres_was_running = args.postgres_service in running
    if paused:
        print("Pausing application services for a consistent backup", file=sys.stderr)
        compose(args, "stop", *paused)
    try:
        yield
    finally:
        if paused:
            compose(args, "up", "-d", *paused)
        elif not postgres_was_running:
            compose(args, "stop", args.postgres_service)


def backup(args: argparse.Namespace) -> None:
    validate_compose(args)
    with paused_stack(args):
        create_backup(args)


def create_backup(args: argparse.Namespace) -> None:
    compose(args, "up", "-d", args.postgres_service)
    wait_for_postgres(args)
    user, database = postgres_identity(args)
    volume = resolved_volume(args, args.evidence_volume)

    if args.output:
        destination = args.output.resolve()
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = (Path("backups") / f"tracynth-{stamp}").resolve()
    if destination.exists():
        raise OpsError(f"backup destination already exists: {destination}")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    if temporary.exists():
        raise OpsError(f"partial backup already exists: {temporary}")
    temporary.mkdir(mode=0o700)

    try:
        database_dump = temporary / "postgres.dump"
        with database_dump.open("wb") as output:
            compose(
                args,
                "exec",
                "-T",
                args.postgres_service,
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--exclude-table-data=django_session",
                f"--username={user}",
                database,
                stdout=output,
            )

        evidence_archive = temporary / "evidence.tar.gz"
        with evidence_archive.open("wb") as output:
            run(
                utility_container(
                    "--mount",
                    f"type=volume,src={volume},dst=/data,readonly",
                    UTILITY_IMAGE,
                    "tar",
                    "-czf",
                    "-",
                    "-C",
                    "/data",
                    ".",
                ),
                stdout=output,
            )
        manifest = {
            "format": 1,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "database": database,
            "files": {
                database_dump.name: sha256(database_dump),
                evidence_archive.name: sha256(evidence_archive),
            },
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    print(f"Backup completed: {destination}")


def verified_backup(path: Path) -> dict:
    directory = path.resolve(strict=True)
    if not directory.is_dir():
        raise OpsError(f"backup is not a directory: {directory}")
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpsError(f"invalid backup manifest: {exc}") from exc
    if manifest.get("format") != 1:
        raise OpsError("unsupported backup format")
    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or set(expected_files) != {
        "postgres.dump",
        "evidence.tar.gz",
    }:
        raise OpsError("backup manifest has an unexpected file set")
    for name, expected_hash in expected_files.items():
        candidate = directory / name
        if not candidate.is_file() or sha256(candidate) != expected_hash:
            raise OpsError(f"backup integrity check failed for {name}")
    try:
        with tarfile.open(directory / "evidence.tar.gz", mode="r:gz") as archive:
            for member in archive:
                parts = Path(member.name.replace("\\", "/")).parts
                if member.name.startswith("/") or ".." in parts:
                    raise OpsError("evidence archive contains an unsafe path")
                if not (member.isfile() or member.isdir()):
                    raise OpsError("evidence archive contains a link or special file")
    except (OSError, tarfile.TarError) as exc:
        raise OpsError(f"invalid evidence archive: {exc}") from exc
    return manifest


def restore(args: argparse.Namespace) -> None:
    if not args.confirm_restore:
        raise OpsError("restore requires --confirm-restore because it replaces current data")
    validate_compose(args)
    backup_directory = args.backup.resolve(strict=True)
    manifest = verified_backup(backup_directory)
    volume = resolved_volume(args, args.evidence_volume)

    safety_args = argparse.Namespace(**vars(args))
    safety_args.output = (
        Path("backups")
        / f"pre-restore-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    backup(safety_args)
    print(f"Pre-restore safety backup completed: {safety_args.output}")

    compose(args, "up", "-d", args.postgres_service)
    wait_for_postgres(args)
    user, database = postgres_identity(args)
    if manifest.get("database") != database:
        raise OpsError(
            f"backup database {manifest.get('database')!r} does not match configured {database!r}"
        )
    compose(args, "stop")
    compose(args, "up", "-d", args.postgres_service)
    wait_for_postgres(args)

    compose(
        args,
        "exec",
        "-T",
        args.postgres_service,
        "dropdb",
        "--if-exists",
        "--force",
        f"--username={user}",
        database,
    )
    compose(
        args,
        "exec",
        "-T",
        args.postgres_service,
        "createdb",
        f"--username={user}",
        "--owner",
        user,
        database,
    )
    with (backup_directory / "postgres.dump").open("rb") as source:
        compose(
            args,
            "exec",
            "-T",
            args.postgres_service,
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
            f"--username={user}",
            "--dbname",
            database,
            stdin=source,
        )

    with (backup_directory / "evidence.tar.gz").open("rb") as source:
        run(
            utility_container(
                "--mount",
                f"type=volume,src={volume},dst=/data",
                UTILITY_IMAGE,
                "/bin/sh",
                "-ec",
                "find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; "
                "tar -xzf - -C /data",
            ),
            stdin=source,
        )
    compose(
        args,
        "run",
        "--rm",
        args.backend_service,
        "python",
        "manage.py",
        "migrate",
        "--noinput",
    )
    compose(
        args,
        "run",
        "--rm",
        args.backend_service,
        "python",
        "manage.py",
        "logout_all_sessions",
    )
    compose(args, "up", "-d", "--wait", "--wait-timeout", "180")
    print("Restore completed and services restarted")


def account(args: argparse.Namespace, command: str) -> None:
    validate_compose(args)
    compose(args, "up", "-d", args.backend_service)
    django_command = ["exec", args.backend_service, "python", "manage.py", command]
    if command == "reset_operator_password" and args.username:
        django_command.append(args.username)
    compose(args, *django_command)


def deploy(args: argparse.Namespace) -> None:
    validate_compose(args)
    security_check = [
        sys.executable,
        str(Path(__file__).with_name("check_compose_security.py")),
        "--proxy-service",
        args.proxy_service,
        "--private-service",
        args.postgres_service,
        "--private-service",
        args.redis_service,
    ]
    if args.compose_file:
        security_check.extend(["--compose-file", str(args.compose_file)])
    run(security_check)
    build_command = ["build"]
    if not args.no_pull:
        build_command.append("--pull")
    compose(args, *build_command)
    compose(args, "up", "-d", args.postgres_service, args.redis_service)
    wait_for_postgres(args)
    compose(
        args,
        "run",
        "--rm",
        args.backend_service,
        "python",
        "manage.py",
        "migrate",
        "--noinput",
    )
    compose(
        args,
        "up",
        "-d",
        "--remove-orphans",
        "--wait",
        "--wait-timeout",
        str(args.wait_timeout),
    )
    compose(args, "ps")


def build_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--compose-file", type=Path)
    result.add_argument("--postgres-service", default="postgres")
    result.add_argument("--redis-service", default="redis")
    result.add_argument("--backend-service", default="backend")
    result.add_argument("--proxy-service", default="caddy")
    result.add_argument("--evidence-volume", default="evidence_data")
    commands = result.add_subparsers(dest="command", required=True)

    backup_parser = commands.add_parser("backup", help="back up PostgreSQL and evidence")
    backup_parser.add_argument("--output", type=Path)

    restore_parser = commands.add_parser("restore", help="replace data from a verified backup")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument("--confirm-restore", action="store_true")

    commands.add_parser("create-account", help="interactively create the initial operator")
    password_parser = commands.add_parser("reset-password", help="interactively reset a password")
    password_parser.add_argument("username", nargs="?")

    deploy_parser = commands.add_parser("deploy", help="build, migrate, and start the stack")
    deploy_parser.add_argument("--no-pull", action="store_true")
    deploy_parser.add_argument("--wait-timeout", type=int, default=180)
    return result


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "backup":
            backup(args)
        elif args.command == "restore":
            restore(args)
        elif args.command == "create-account":
            account(args, "create_initial_user")
        elif args.command == "reset-password":
            account(args, "reset_operator_password")
        else:
            deploy(args)
    except (OpsError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
