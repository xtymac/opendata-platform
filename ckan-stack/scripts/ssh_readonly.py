#!/usr/bin/env python3
"""Read-only SSH helper for the CKAN assistant."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import PurePosixPath
from typing import Iterable

DEFAULT_ALLOWED_ROOTS = "/var/log:/etc:/srv/app"
DEFAULT_TAIL_LINES = 200
MAX_BYTES = 20000


class ConfigError(Exception):
    """Raised when required SSH configuration is missing."""


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def allowed_roots() -> list[str]:
    raw = env("SSH_ASSISTANT_ALLOWED_ROOTS", DEFAULT_ALLOWED_ROOTS) or ""
    return [root.rstrip("/") for root in raw.split(":") if root.strip()]


def normalise_path(path: str) -> str:
    if not path:
        raise ValueError("path is required")

    pure = PurePosixPath(path)
    if pure.is_absolute():
        normalised = str(pure)
    else:
        normalised = "/" + str(pure)

    roots = allowed_roots()
    if roots:
        for root in roots:
            prefix = root if root == "/" else root + "/"
            if normalised == root or normalised.startswith(prefix):
                return normalised
        raise ValueError(f"Path '{normalised}' is outside allowed roots: {roots}")

    return normalised


def build_remote_command(path: str, tail_lines: int | None, max_bytes: int) -> list[str]:
    if tail_lines and tail_lines > 0:
        return ["tail", "-n", str(tail_lines), path]
    return ["head", "-c", str(max_bytes), path]


def build_ssh_command(remote_cmd: list[str]) -> list[str]:
    host = env("SSH_ASSISTANT_HOST")
    if not host:
        raise ConfigError("SSH_ASSISTANT_HOST is not set")

    username = env("SSH_ASSISTANT_USERNAME", "ubuntu")
    key_path = env("SSH_ASSISTANT_KEY_PATH")
    known_hosts = env("SSH_ASSISTANT_KNOWN_HOSTS")

    cmd: list[str] = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
    ]

    if known_hosts:
        cmd.extend(["-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={known_hosts}"])
    else:
        cmd.extend([
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
        ])

    if key_path:
        cmd.extend(["-i", key_path])

    cmd.append(f"{username}@{host}")
    cmd.extend(remote_cmd)
    return cmd


def run_subprocess(cmd: Iterable[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        check=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only SSH helper")
    parser.add_argument("--path", required=True, help="Absolute path on the remote host")
    parser.add_argument("--tail", type=int, default=None, help="Optional number of trailing lines to fetch")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=MAX_BYTES,
        help=f"Maximum bytes to return when tail is not specified (default {MAX_BYTES})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        normalised_path = normalise_path(args.path)
    except ValueError as exc:
        payload = {"error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False))
        return 2

    try:
        remote_command = build_remote_command(normalised_path, args.tail, args.max_bytes)
        ssh_command = build_ssh_command(remote_command)
    except ConfigError as exc:
        payload = {"error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False))
        return 2

    result = run_subprocess(ssh_command)

    if result.returncode != 0:
        payload = {
            "error": result.stderr.strip() or result.stdout.strip() or f"SSH exited with {result.returncode}",
            "path": normalised_path,
            "returncode": result.returncode,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return result.returncode or 1

    content = result.stdout
    if len(content) > args.max_bytes:
        content = content[: args.max_bytes] + "\n... (truncated)"

    payload = {
        "path": normalised_path,
        "tail": args.tail if args.tail and args.tail > 0 else None,
        "content": content,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
