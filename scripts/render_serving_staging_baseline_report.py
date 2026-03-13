from __future__ import annotations

import argparse
from pathlib import Path

from ml_lifecycle_platform.ci.serving_staging_baseline import (
    render_baseline_markdown_from_paths,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a markdown report from k6 staging baseline artifacts."
    )
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--context-json", required=True)
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = render_baseline_markdown_from_paths(
        summary_json_path=Path(args.summary_json),
        context_json_path=Path(args.context_json),
    )
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
