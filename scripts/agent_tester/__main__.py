"""CLI entry point: python -m scripts.agent_tester [OPTIONS]"""

from __future__ import annotations

from .config import parse_args
from .runner import run_all


def main() -> None:
    config = parse_args()
    run_all(config)


if __name__ == "__main__":
    main()
