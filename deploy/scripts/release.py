#!/usr/bin/env python3
"""Validate an immutable release manifest without executing its contents."""

import argparse
import re
from pathlib import Path

RULES = {
    "BACKEND_IMAGE": r"[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}",
    "FRONTEND_IMAGE": r"[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}",
    "GIT_COMMIT": r"[a-f0-9]{40}",
    "APP_VERSION": r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}",
}


def read_release(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (
            not separator
            or key not in RULES
            or key in values
            or not re.fullmatch(RULES[key], value)
        ):
            raise ValueError("Invalid release: require unique approved keys and immutable digests")
        values[key] = value
    if set(values) != set(RULES):
        raise ValueError("Release requires BACKEND_IMAGE, FRONTEND_IMAGE, GIT_COMMIT, APP_VERSION")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        values = read_release(args.manifest)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    for key in RULES:
        print(f"{key}={values[key]}")


if __name__ == "__main__":
    main()
