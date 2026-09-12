#!/usr/bin/env python3
"""Check public same-origin routes; credentials and cookies stay out of output."""

import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    parsed_base = urlsplit(base)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
        print("FAIL: BASE_URL must be an HTTP(S) origin", file=sys.stderr)
        return 1
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def request(path: str, payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            base + path,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Requested-With": "AulaData",
                "Origin": origin,
            },
        )
        with client.open(req, timeout=6) as response:
            body = response.read()
            return (
                json.loads(body)
                if body and "json" in response.headers.get("Content-Type", "")
                else None
            )

    try:
        for attempt in range(15):
            try:
                health = request("/health")
                ready = request("/ready")
                break
            except (urllib.error.URLError, TimeoutError):
                if attempt == 14:
                    raise
                time.sleep(2)
        if not isinstance(health, dict) or health.get("status") != "ok":
            raise ValueError("Health payload is invalid")
        if not isinstance(ready, dict) or ready.get("database") != "ok":
            raise ValueError("PostgreSQL readiness payload is invalid")
        for env_key, health_key in (
            ("APP_ENV", "environment"),
            ("APP_VERSION", "version"),
            ("GIT_COMMIT", "commit"),
        ):
            expected = os.environ.get(env_key)
            if expected and health.get(health_key) != expected:
                raise ValueError(f"Runtime metadata mismatch: {health_key}")
        if not args.health_only:
            email, password = os.environ.get("SMOKE_EMAIL"), os.environ.get("SMOKE_PASSWORD")
            if not email or not password:
                raise ValueError("SMOKE_EMAIL and SMOKE_PASSWORD must be set")
            request("/login")
            request("/api/v1/auth/login", {"email": email, "password": password})
            user = request("/api/v1/auth/me")
            if not isinstance(user, dict) or user.get("email", "").lower() != email.lower():
                raise ValueError("Authenticated session did not match smoke user")
            classrooms = request("/api/v1/classrooms")
            if not isinstance(classrooms, dict) or not isinstance(classrooms.get("items"), list):
                raise ValueError("Classroom listing payload is invalid")
            request("/api/v1/auth/logout", {})
            try:
                request("/api/v1/auth/me")
            except urllib.error.HTTPError as exc:
                if exc.code != 401:
                    raise
            else:
                raise ValueError("Logout did not clear the authenticated session")
        print(
            "PASS: health, PostgreSQL readiness, expected runtime metadata"
            + ("" if args.health_only else ", frontend, login, session, classroom listing, logout")
        )
        return 0
    except urllib.error.HTTPError as exc:
        print(
            f"FAIL: smoke HTTP {exc.code}; check server logs without exposing credentials",
            file=sys.stderr,
        )
    except (urllib.error.URLError, TimeoutError):
        print("FAIL: smoke could not reach a healthy service", file=sys.stderr)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
