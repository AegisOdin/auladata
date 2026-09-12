#!/usr/bin/env python3
"""Create a PostgreSQL custom-format backup without putting passwords in argv."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def main() -> int:
    os.umask(0o077)
    url = urlsplit(os.environ.get("DATABASE_URL", ""))
    if url.scheme != "postgresql+psycopg" or not url.hostname or not url.path.strip("/"):
        print("Invalid PostgreSQL configuration for backup", file=sys.stderr)
        return 1
    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": url.hostname,
            "PGPORT": str(url.port or 5432),
            "PGUSER": unquote(url.username or ""),
            "PGPASSWORD": unquote(url.password or ""),
            "PGDATABASE": unquote(url.path.lstrip("/")),
            "PGSSLMODE": parse_qs(url.query).get("sslmode", ["prefer"])[0],
            "PGCONNECT_TIMEOUT": "10",
        }
    )
    folder = Path(os.environ.get("BACKUP_DIR", "/var/backups/auladata"))
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = folder / f"auladata-{timestamp}.dump"
    temporary = destination.with_suffix(".dump.partial")
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        os.environ.get("BACKUP_DOCKER_NETWORK", "host"),
    ]
    for key in (
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
        "PGSSLMODE",
        "PGCONNECT_TIMEOUT",
    ):
        command += ["--env", key]
    command += [
        os.environ.get("BACKUP_IMAGE", "postgres:17-alpine"),
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
    ]
    try:
        with temporary.open("xb") as output:
            subprocess.run(command, env=environment, stdout=output, check=True)
        if not temporary.stat().st_size:
            raise ValueError("Empty database backup")
        # Parse only this archive in a read-only mount, without network access.
        # A file mount also avoids Docker Desktop hanging on redirected file stdin.
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--mount",
                f"type=bind,source={temporary.resolve()},target=/backup.dump,readonly",
                os.environ.get("BACKUP_IMAGE", "postgres:17-alpine"),
                "pg_restore",
                "--list",
                "/backup.dump",
            ],
            stdout=subprocess.DEVNULL,
            check=True,
            timeout=60,
        )
        temporary.replace(destination)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError):
        temporary.unlink(missing_ok=True)
        print("Backup failed; deployment must stop before migrations", file=sys.stderr)
        return 1
    print(f"Backup ready: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
