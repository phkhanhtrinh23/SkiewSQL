"""Render a persisted SkiewSQL registry as a PNG or SVG.

The registry JSON remains a flat ViewSpec catalog. This optional utility builds
a temporary dependency diagram solely for presentation.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx

from skiewsql import sqlview


CATEGORY_COLORS = {
    "SEL": "#B9D7F5",
    "SEM": "#D7C5F5",
    "AGG": "#F7C99E",
    "JOIN": "#A8E0CF",
    "RANK": "#F5B7B1",
    "WIN": "#F8E49A",
    "RESHAPE": "#C7D3DD",
    "SET": "#D5E8B0",
    "REC": "#E2B5D3",
    "NORM": "#B6E3A8",
}


def _brief(items: Sequence[str], limit: int = 3) -> str:
    vals = [str(x) for x in (items or [])]
    if not vals:
        return "—"
    shown = vals[:limit]
    return ", ".join(shown) + (f" +{len(vals) - limit}" if len(vals) > limit else "")


def _label(registry, display, node: str) -> str:
    data = display.nodes[node]
    if data.get("kind") == "skill":
        category = data.get("category", node.split("::", 1)[-1])
        return f"SKILL\n{category}"
    name = node.split("::", 1)[-1]
    spec = registry.views.get(name)
    if spec is None:
        return name
    return (
        f"{spec.name}\n"
        f"[{spec.category}]\n"
        f"out: {_brief(spec.output_columns)}\n"
        f"grain: {_brief(spec.grain, 2)}"
    )


def _category_layout(graph: nx.DiGraph) -> Dict[str, tuple[float, float]]:
    """Stable two-column layout: category nodes left, their view instances in category bands. Dependency edges may cross category bands, which makes cross-skill composition visible.  This is more deterministic and legible for persisted graphs than a random force-directed layout."""
    categories: Dict[str, List[str]] = {}
    skill_nodes: Dict[str, str] = {}
    for node, data in graph.nodes(data=True):
        cat = str(data.get("category", "OTHER"))
        if data.get("kind") == "skill":
            skill_nodes[cat] = node
        else:
            categories.setdefault(cat, []).append(node)
    ordered = sorted(set(categories) | set(skill_nodes))
    pos: Dict[str, tuple[float, float]] = {}
    for ci, cat in enumerate(ordered):
        y0 = -float(ci) * 2.2
        if cat in skill_nodes:
            pos[skill_nodes[cat]] = (0.0, y0)
        nodes = sorted(categories.get(cat, []))
        for i, node in enumerate(nodes):
            # Up to six nodes per row keeps labels from becoming a single extremely wide strip.
            row, col = divmod(i, 6)
            pos[node] = (2.4 + col * 2.65, y0 - row * 1.35)
    return pos


def render_registry(input_path: str, output_path: str, *, highlight: Iterable[str] = (),
                    focus: Iterable[str] = (), title: str = "", dpi: int = 180) -> Path:
    registry = sqlview.load_registry(input_path)
    display = nx.DiGraph()
    for spec in registry.views.values():
        vid, cid = f"view::{spec.name}", f"category::{spec.category}"
        display.add_node(vid, kind="view", category=spec.category)
        display.add_node(cid, kind="skill", category=spec.category)
        display.add_edge(cid, vid, etype="INSTANCE_OF")
    for spec in registry.views.values():
        for dependency in spec.depends_on:
            if dependency in registry.views:
                display.add_edge(f"view::{spec.name}", f"view::{dependency}",
                                 etype="DEPENDS_ON")
    focus_ids = {f"view::{name.strip()}" for name in focus if name.strip()}
    if focus_ids:
        missing = sorted(n for n in focus_ids if n not in display)
        if missing:
            raise ValueError(f"unknown focused view(s): {', '.join(missing)}")
        # DEPENDS_ON is stored dependent -> dependency, so descendants over DEPENDS_ON edges are the transitive dependency closure.
        deps = nx.DiGraph([(u, v) for u, v, d in display.edges(data=True) if d.get("etype") == "DEPENDS_ON"])
        kept_views = set(focus_ids)
        for node in list(focus_ids):
            if node in deps:
                kept_views.update(nx.descendants(deps, node))
        display = display.subgraph(kept_views).copy()
    pos = _category_layout(display)
    highlighted = {f"view::{name.strip()}" for name in highlight if name.strip()}

    view_nodes = [n for n, d in display.nodes(data=True) if d.get("kind") == "view"]
    skill_nodes = [n for n, d in display.nodes(data=True) if d.get("kind") == "skill"]
    orphan_nodes = [n for n, d in display.nodes(data=True) if not d.get("kind")]
    labels = {n: _label(registry, display, n) for n in display.nodes}

    n_views = max(1, len(view_nodes))
    if focus_ids:
        # A compact canvas makes a small explanatory dependency closure readable without the large empty category bands that are useful for the complete graph.
        width = max(11.0, min(17.0, 8.5 + math.sqrt(n_views) * 2.0))
        height = max(6.5, min(10.0, 5.0 + len(skill_nodes) * 1.2))
    else:
        width = max(18.0, min(34.0, 15.0 + math.sqrt(n_views) * 2.5))
        height = max(10.0, min(26.0, 8.0 + len(skill_nodes) * 2.0))
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_axis_off()

    # Category nodes are capability/type buckets, not executable CTEs.
    nx.draw_networkx_nodes(
        display, pos, nodelist=skill_nodes, node_shape="h", node_size=3100,
        node_color="#27374D", edgecolors="#17202A", linewidths=1.5, ax=ax,
    )

    normal_views = [n for n in view_nodes if n not in highlighted]
    view_colors = [CATEGORY_COLORS.get(display.nodes[n].get("category"), "#D9D9D9")
                   for n in normal_views]
    nx.draw_networkx_nodes(
        display, pos, nodelist=normal_views, node_shape="o", node_size=5200,
        node_color=view_colors, edgecolors="#506070", linewidths=1.1, ax=ax,
    )
    if highlighted:
        hi = [n for n in view_nodes if n in highlighted]
        nx.draw_networkx_nodes(
            display, pos, nodelist=hi, node_shape="o", node_size=5900,
            node_color="#FFE082", edgecolors="#C62828", linewidths=3.0, ax=ax,
        )
    if orphan_nodes:
        nx.draw_networkx_nodes(
            display, pos, nodelist=orphan_nodes, node_shape="o", node_size=4200,
            node_color="#EEEEEE", edgecolors="#9E9E9E", linewidths=1.0, ax=ax,
        )

    inst_edges = []                                       # category nodes were removed from the graph
    dep_edges = [(u, v) for u, v, d in display.edges(data=True)
                 if d.get("etype") == "DEPENDS_ON"]
    nx.draw_networkx_edges(
        display, pos, edgelist=inst_edges, edge_color="#AAB7B8", style="dotted",
        width=1.2, arrows=True, arrowstyle="-|>", arrowsize=13,
        connectionstyle="arc3,rad=0.04", ax=ax,
    )
    nx.draw_networkx_edges(
        display, pos, edgelist=dep_edges, edge_color="#1565C0", style="solid",
        width=2.2, arrows=True, arrowstyle="-|>", arrowsize=16,
        connectionstyle="arc3,rad=0.10", ax=ax,
    )

    # White text for dark skill nodes. Dark text for executable view nodes.
    nx.draw_networkx_labels(
        display, pos, labels={n: labels[n] for n in view_nodes + orphan_nodes},
        font_size=7.2, font_color="#17202A", font_weight="normal", ax=ax,
    )
    nx.draw_networkx_labels(
        display, pos, labels={n: labels[n] for n in skill_nodes},
        font_size=8.5, font_color="white", font_weight="bold", ax=ax,
    )

    legend = [
        Line2D([0], [0], marker="h", color="w", label="skill/category node",
               markerfacecolor="#27374D", markeredgecolor="#17202A", markersize=13),
        Line2D([0], [0], marker="o", color="w", label="stored executable ViewSpec",
               markerfacecolor="#B9D7F5", markeredgecolor="#506070", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="highlighted reuse example",
               markerfacecolor="#FFE082", markeredgecolor="#C62828", markersize=12),
        Line2D([0], [0], color="#1565C0", linewidth=2.2,
               label="DEPENDS_ON (dependent → dependency)"),
    ]
    if focus_ids:
        ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.05),
                  ncol=3, frameon=True, fontsize=8)
        ax.margins(x=0.16, y=0.22)
    else:
        ax.legend(handles=legend, loc="lower left", frameon=True, fontsize=9)
        ax.margins(x=0.04, y=0.08)
    graph_title = title or f"SkiewSQL skill registry — {registry.db_id}"
    dep_word = "edge" if len(dep_edges) == 1 else "edges"
    ax.set_title(
        f"{graph_title}\n{len(view_nodes)} stored views · {len(dep_edges)} dependency {dep_word}\n"
        "Node labels are snippets. Full SQL and contracts are in the sibling Markdown skill cards.",
        fontsize=13 if focus_ids else 16, fontweight="bold", pad=18,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize a persisted SkiewSQL SkillRegistry.")
    parser.add_argument("--input", required=True, help="canonical registry JSON")
    parser.add_argument("--output", required=True, help="output .png or .svg path")
    parser.add_argument("--highlight", default="",
                        help="comma-separated view names to outline in red")
    parser.add_argument("--focus", default="",
                        help="show only these views, their dependencies, and category nodes")
    parser.add_argument("--title", default="")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()
    names = [x.strip() for x in args.highlight.split(",") if x.strip()]
    focus = [x.strip() for x in args.focus.split(",") if x.strip()]
    out = render_registry(args.input, args.output, highlight=names, focus=focus,
                       title=args.title, dpi=args.dpi)
    print(os.path.abspath(out))


if __name__ == "__main__":
    main()
