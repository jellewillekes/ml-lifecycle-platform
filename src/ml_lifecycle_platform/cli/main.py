from __future__ import annotations

import argparse
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlp",
        description="ML Lifecycle Platform CLI (UP-02 placeholder)",
    )
    subparsers = parser.add_subparsers(dest="command")

    pipeline = subparsers.add_parser("pipeline", help="Pipeline commands")
    pipeline_sub = pipeline.add_subparsers(dest="pipeline_command")
    pipeline_sub.add_parser("run", help="Run pipeline (placeholder)")

    registry = subparsers.add_parser("registry", help="Registry commands")
    registry_sub = registry.add_subparsers(dest="registry_command")
    registry_sub.add_parser("promote", help="Promote candidate (placeholder)")
    registry_sub.add_parser("rollback", help="Rollback prod (placeholder)")
    registry_sub.add_parser("reproduce", help="Reproduce model (placeholder)")

    serve = subparsers.add_parser("serve", help="Serving commands")
    serve_sub = serve.add_subparsers(dest="serve_command")
    serve_sub.add_parser("api", help="Run serving API (placeholder)")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    print(
        "UP-02 placeholder CLI. Continue using existing module entrypoints and "
        "Make targets until runtime wiring lands."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
