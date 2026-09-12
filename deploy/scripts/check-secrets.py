#!/usr/bin/env python3
"""Basic tracked-file hygiene gate; not a substitute for a full secret scanner."""

import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    patterns = [
        re.compile(rb"-----BEGIN " + rb"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(rb"gh[pousr]_" + rb"[A-Za-z0-9]{36,}"),
        re.compile(rb"github_pat_" + rb"[A-Za-z0-9_]{40,}"),
    ]
    failures = []
    for name in filter(None, names):
        path = Path(name)
        if not path.is_file():
            continue
        if (
            path.name == ".env"
            or (path.name.startswith(".env.") and path.name != ".env.example")
            or name.endswith((".pem", ".key", ".p12", ".dump"))
            or (name.startswith("deploy/env/") and name.endswith(".env"))
        ):
            failures.append(name)
            continue
        if path.stat().st_size <= 2_000_000:
            content = path.read_bytes()
            if any(pattern.search(content) for pattern in patterns):
                failures.append(name)
    if failures:
        print("Secret hygiene failed (contents omitted): " + ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: tracked env/private-key/token hygiene")
    return 0


if __name__ == "__main__":
    sys.exit(main())
