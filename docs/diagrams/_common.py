"""Shared helpers for the M4 architecture diagrams.

Conventions:
  - One Diagram per file; output filename matches the source basename.
  - Edges crossing a port boundary carry the contract name as their label.
  - Local diagrams render OSS equivalents declared in the M4 portability rule;
    hosted diagrams render the GCP services those adapters target.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from diagrams import Edge
from diagrams.custom import Custom
from diagrams.generic.blank import Blank

ASSETS_DIR: Final[Path] = Path(__file__).parent / "assets"
OUTPUT_DIR: Final[Path] = Path(__file__).parent

GRAPH_ATTR: Final[dict[str, str]] = {
    "fontname": "Helvetica",
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.6",
    "splines": "spline",
    "nodesep": "0.6",
    "ranksep": "0.9",
}

NODE_ATTR: Final[dict[str, str]] = {
    "fontname": "Helvetica",
    "fontsize": "12",
}

EDGE_ATTR: Final[dict[str, str]] = {
    "fontname": "Helvetica",
    "fontsize": "10",
}

CLUSTER_COLORS: Final[dict[str, str]] = {
    "data_sources": "#fff4e6",
    "pipeline": "#e7f1ff",
    "registry": "#e9f7ef",
    "serving": "#f3e8ff",
    "event_plane": "#fde2e2",
    "observability": "#eceff1",
    "ci_cd": "#fff9c4",
    "external": "#ffffff",
    "gcp": "#e8f0fe",
    "local": "#f1f3f4",
}


def cluster_attr(kind: str) -> dict[str, str]:
    """Cluster style for a given domain colour key."""
    return {
        "bgcolor": CLUSTER_COLORS.get(kind, "#ffffff"),
        "fontname": "Helvetica-Bold",
        "fontsize": "13",
        "style": "rounded,filled",
        "pencolor": "#444444",
        "margin": "16",
    }


def brand(label: str, asset: str) -> Custom | Blank:
    """Return a Custom node if the brand PNG exists, otherwise a labeled Blank.

    Lets diagrams render even when an optional logo download has failed.
    Missing assets are listed in the diagrams README so contributors can fix
    them later without blocking the build.
    """
    path = ASSETS_DIR / asset
    if path.exists():
        return Custom(label, str(path))
    return Blank(label)


def contract(name: str) -> Edge:
    """Edge labelled with a contract type — used for port boundary crossings."""
    return Edge(label=name, fontsize="10", fontname="Helvetica-Oblique")


def signal(name: str) -> Edge:
    """Edge labelled with a non-contract signal (HTTP request, alert webhook)."""
    return Edge(label=name, fontsize="10", fontname="Helvetica", style="dashed")


def plain() -> Edge:
    """Unlabelled internal edge."""
    return Edge()
