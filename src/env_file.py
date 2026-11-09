"""
env_file.py - Read KEY=VALUE lines from the project's .env file into the environment.

Used so that FastF1 finds F1_USERNAME and F1_PASSWORD without them ever being
typed into a command. Real environment variables win over the file. Values are
never printed.
"""

import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / ".env"


def read_env_file(path: Path = DEFAULT_PATH) -> dict[str, str]:
    """Parse KEY=VALUE lines. Blank lines, comments and empty values are skipped."""
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if value:
            values[key.strip()] = value
    return values


def load_env_file(path: Path = DEFAULT_PATH) -> None:
    """Put the file's values into os.environ, without overriding variables already set."""
    for key, value in read_env_file(path).items():
        os.environ.setdefault(key, value)
