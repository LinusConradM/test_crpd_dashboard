#!/usr/bin/env python3
"""
Visualization script — Phase 4: Policy Brief Generation (CRPD Dashboard)
=========================================================================
Reads eval_results_phase4.json and produces 6 interactive Plotly charts
saved to LLM_Development/charts/.

Charts (2 IR/RAG lens, 2 LLM-as-Judge lens, 2 cross-lens):
  phase4_ir_metrics.html       — grouped bar: MRR, nDCG, Recall, Precision per config
  phase4_ir_latency.html       — scatter: IR score vs retrieval latency
  phase4_judge_quality.html    — grouped bar: accuracy/completeness/relevance/groundedness
  phase4_judge_heatmap.html    — heatmap: per-question judge scores
  phase4_radar_ir_vs_judge.html — radar: IR polygon vs Judge polygon per config
  phase4_scatter_ir_vs_judge.html — scatter: avg IR score vs avg judge score per config

Usage:
  python LLM_Development/visualize_phase4.py

Run evaluate_phase4.py first to generate eval_results_phase4.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ── Path setup ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_PATH = Path(__file__).parent / "eval_results_phase4.json"
CHARTS_DIR = Path(__file__).parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# ── Color palette (from src/colors.py — project standard) ────────────────────
from src.colors import CATEGORICAL_PALETTE


# Config colours (one per config, consistent across all charts)
CONFIG_COLORS = {
    "config_A": CATEGORICAL_PALETTE[0],  # UN Blue
    "config_B": CATEGORICAL_PALETTE[2],  # Bluish Green
    "config_C": CATEGORICAL_PALETTE[1],  # Vermillion
    "config_D": CATEGORICAL_PALETTE[5],  # Orange
}
CONFIG_LABELS = {
    "config_A": "A: mpnet + Groq (baseline)",
    "config_B": "B: MiniLM + Groq",
    "config_C": "C: mpnet + Ollama",
    "config_D": "D: mpnet + Rewrite + Groq",
}

UN_BLUE = CATEGORICAL_PALETTE[0]  # #003F87
PASS_THRESHOLD = 3.5
MRR_TARGET = 0.70
NDCG_TARGET = 0.80

# Shared layout defaults
_FONT = {"family": "Inter, sans-serif", "size": 13, "color": "#191C1F"}
_PAPER_BG = "#FFFFFF"
_PLOT_BG = "#F8F9FA"
_GRID_COLOR = "#E0E4ED"


def _base_layout(title: str, lens: str) -> dict:
    """Return a shared layout dict. lens = 'IR/RAG' | 'LLM-as-Judge' | 'Cross-Lens'"""
    lens_colors = {
        "IR/RAG": "#003F87",
        "LLM-as-Judge": "#009E73",
        "Cross-Lens": "#882255",
    }
    lens_color = lens_colors.get(lens, UN_BLUE)
    return {
        "title": {
            "text": (f"<b style='color:{lens_color}'>[{lens}]</b>  {title}"),
            "font": {"size": 16, "family": "Inter, sans-serif", "color": "#191C1F"},
            "x": 0.02,
            "xanchor": "left",
        },
        "font": _FONT,
        "paper_bgcolor": _PAPER_BG,
        "plot_bgcolor": _PLOT_BG,
        "legend": {
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": _GRID_COLOR,
            "borderwidth": 1,
        },
        "margin": {"t": 80, "b": 60, "l": 60, "r": 40},
    }


def _save(fig: go.Figure, filename: str) -> None:
    out = CHARTS_DIR / filename
    fig.write_html(str(out), include_plotlyjs=True)
    print(f"  Saved → {out}")


def _active_configs(data: dict) -> list[str]:
    """Return config IDs that were not skipped."""
    return [cid for cid, v in data["configs"].items() if not v.get("skipped")]


# ── Chart 1: IR metrics bar chart ─────────────────────────────────────────────


def chart_ir_metrics(data: dict) -> None:
    """Grouped bar: MRR, nDCG@10, Recall@5, Recall@10, Precision@5 per config."""
    metrics = ["mrr", "ndcg_10", "recall_5", "recall_10", "precision_5"]
    metric_labels = ["MRR", "nDCG@10", "Recall@5", "Recall@10", "Precision@5"]
    active = _active_configs(data)

    rows = []
    for cid in active:
        scores = data["configs"][cid]["scores"]
        for m, ml in zip(metrics, metric_labels, strict=False):
            rows.append(
                {
                    "config": CONFIG_LABELS.get(cid, cid),
                    "metric": ml,
                    "value": scores.get(m, 0),
                    "color": CONFIG_COLORS.get(cid, UN_BLUE),
                }
            )

    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="metric",
        y="value",
        color="config",
        barmode="group",
        color_discrete_map={
            CONFIG_LABELS.get(cid, cid): CONFIG_COLORS.get(cid, UN_BLUE) for cid in active
        },
        labels={"value": "Score (0–1)", "metric": "Metric", "config": "Config"},
    )

    # Reference lines
    fig.add_hline(
        y=MRR_TARGET,
        line_dash="dash",
        line_color="#D55E00",
        annotation_text=f"MRR target ({MRR_TARGET})",
        annotation_position="top right",
        annotation_font_color="#D55E00",
    )
    fig.add_hline(
        y=NDCG_TARGET,
        line_dash="dot",
        line_color="#882255",
        annotation_text=f"nDCG target ({NDCG_TARGET})",
        annotation_position="bottom right",
        annotation_font_color="#882255",
    )

    layout = _base_layout("IR Metrics per Config — Retrieval Pipeline Quality", "IR/RAG")
    layout.update(
        {
            "yaxis": {"range": [0, 1.05], "gridcolor": _GRID_COLOR, "title": "Score (0–1)"},
            "xaxis": {"gridcolor": _GRID_COLOR, "title": ""},
        }
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_ir_metrics.html")


# ── Chart 2: IR score vs retrieval latency scatter ────────────────────────────


def chart_ir_latency(data: dict) -> None:
    """Scatter: x = avg retrieval latency (ms), y = MRR; size = nDCG."""
    active = _active_configs(data)
    rows = []
    for cid in active:
        scores = data["configs"][cid]["scores"]
        rows.append(
            {
                "config": CONFIG_LABELS.get(cid, cid),
                "mrr": scores.get("mrr", 0),
                "ndcg": scores.get("ndcg_10", 0),
                "latency_ms": scores.get("avg_retrieval_latency_ms", 0),
                "color": CONFIG_COLORS.get(cid, UN_BLUE),
            }
        )

    df = pd.DataFrame(rows)
    fig = px.scatter(
        df,
        x="latency_ms",
        y="mrr",
        size="ndcg",
        color="config",
        text="config",
        size_max=40,
        color_discrete_map={
            CONFIG_LABELS.get(cid, cid): CONFIG_COLORS.get(cid, UN_BLUE) for cid in active
        },
        labels={"latency_ms": "Avg Retrieval Latency (ms)", "mrr": "MRR", "config": "Config"},
    )
    fig.update_traces(textposition="top center", marker_line_color="white", marker_line_width=1.5)

    # Target line
    fig.add_hline(
        y=MRR_TARGET,
        line_dash="dash",
        line_color="#D55E00",
        annotation_text=f"MRR target ({MRR_TARGET})",
        annotation_font_color="#D55E00",
    )

    layout = _base_layout(
        "Retrieval Quality vs Latency — Faster configs that sacrifice MRR are visible here",
        "IR/RAG",
    )
    layout.update(
        {
            "yaxis": {"range": [0, 1.05], "gridcolor": _GRID_COLOR, "title": "MRR (↑ better)"},
            "xaxis": {"gridcolor": _GRID_COLOR, "title": "Avg Retrieval Latency (ms) (← faster)"},
        }
    )
    fig.add_annotation(
        text="Bubble size = nDCG@10",
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.02,
        showarrow=False,
        font={"size": 11, "color": "#6B7280"},
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_ir_latency.html")


# ── Chart 3: LLM-as-Judge quality bar chart ───────────────────────────────────


def chart_judge_quality(data: dict) -> None:
    """Grouped bar: accuracy, completeness, relevance, groundedness per config."""
    dims = ["accuracy", "completeness", "relevance", "groundedness"]
    dim_labels = ["Accuracy", "Completeness", "Relevance", "Groundedness"]
    active = _active_configs(data)

    rows = []
    for cid in active:
        scores = data["configs"][cid]["scores"]
        for d, dl in zip(dims, dim_labels, strict=False):
            rows.append(
                {
                    "config": CONFIG_LABELS.get(cid, cid),
                    "dimension": dl,
                    "score": scores.get(d, 0),
                }
            )

    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="dimension",
        y="score",
        color="config",
        barmode="group",
        color_discrete_map={
            CONFIG_LABELS.get(cid, cid): CONFIG_COLORS.get(cid, UN_BLUE) for cid in active
        },
        labels={"score": "Score (1–5)", "dimension": "Dimension", "config": "Config"},
    )

    # Pass threshold
    fig.add_hline(
        y=PASS_THRESHOLD,
        line_dash="dash",
        line_color="#009E73",
        annotation_text=f"Pass threshold ({PASS_THRESHOLD})",
        annotation_font_color="#009E73",
    )

    layout = _base_layout("Answer Quality per Config — LLM-as-Judge Evaluation", "LLM-as-Judge")
    layout.update(
        {
            "yaxis": {"range": [0, 5.3], "gridcolor": _GRID_COLOR, "title": "Score (1–5)"},
            "xaxis": {"gridcolor": _GRID_COLOR, "title": ""},
        }
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_judge_quality.html")


# ── Chart 4: Per-question heatmap ─────────────────────────────────────────────


def chart_judge_heatmap(data: dict) -> None:
    """Heatmap: rows = questions, cols = judge dimensions."""
    dims = ["accuracy", "completeness", "relevance", "groundedness"]
    dim_labels = ["Accuracy", "Completeness", "Relevance", "Groundedness"]
    active = _active_configs(data)

    # Use the winner config for the heatmap (most informative for per-question view)
    winner = data.get("winner", active[0] if active else "config_A")
    if winner not in active:
        winner = active[0]

    config_data = data["configs"][winner]
    per_q = config_data.get("per_question", [])

    question_ids = []
    matrix = []

    for q_result in per_q:
        j = q_result.get("judge_scores", {})
        if not j or "error" in j:
            continue
        row_scores = [j.get(d, 0) for d in dims]
        question_ids.append(q_result["id"])
        matrix.append(row_scores)

    if not matrix:
        print("  [WARN] No valid judge scores for heatmap — skipping chart 4")
        return

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=dim_labels,
            y=question_ids,
            colorscale=[
                [0.0, "#FEE2E2"],
                [0.35, "#FEF9C3"],
                [0.7, "#DCFCE7"],
                [1.0, "#003F87"],
            ],
            zmin=1,
            zmax=5,
            text=[[f"{v:.1f}" for v in row] for row in matrix],
            texttemplate="%{text}",
            textfont={"size": 11},
            colorbar={
                "title": "Score",
                "tickvals": [1, 2, 3, 4, 5],
                "ticktext": ["1", "2", "3", "4", "5"],
            },
        )
    )

    layout = _base_layout(
        f"Per-Question Judge Scores ({CONFIG_LABELS.get(winner, winner)}) — reveals where the config struggles",
        "LLM-as-Judge",
    )
    layout.update(
        {
            "xaxis": {"title": "Dimension"},
            "yaxis": {"title": "Test Question"},
            "height": max(300, len(question_ids) * 50 + 150),
        }
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_judge_heatmap.html")


# ── Chart 5: Radar — IR vs Judge per config ────────────────────────────────────


def chart_radar_ir_vs_judge(data: dict) -> None:
    """
    Radar with two overlapping polygons per config:
    IR lens (MRR, nDCG, Recall@5, Precision@5 — normalized 0–1)
    Judge lens (accuracy, completeness, relevance, groundedness — normalized 0–1 from 1–5)
    """
    active = _active_configs(data)

    ir_metrics = ["mrr", "ndcg_10", "recall_5", "precision_5"]
    ir_labels = ["MRR", "nDCG@10", "Recall@5", "Precision@5"]
    judge_metrics = ["accuracy", "completeness", "relevance", "groundedness"]
    judge_labels = ["Accuracy", "Completeness", "Relevance", "Groundedness"]

    # Interleave IR and Judge for a combined radar
    categories = ir_labels + judge_labels
    categories_closed = [*categories, categories[0]]

    fig = go.Figure()

    for cid in active:
        scores = data["configs"][cid]["scores"]
        color = CONFIG_COLORS.get(cid, UN_BLUE)

        ir_vals = [scores.get(m, 0) for m in ir_metrics]
        judge_vals = [(scores.get(m, 0) - 1) / 4 for m in judge_metrics]  # normalize 1–5 → 0–1
        all_vals = ir_vals + judge_vals
        all_vals_closed = [*all_vals, all_vals[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=all_vals_closed,
                theta=categories_closed,
                fill="toself",
                fillcolor=f"rgba{(*tuple(int(color.lstrip('#')[i : i + 2], 16) for i in (0, 2, 4)), 0.15)}",
                line={"color": color, "width": 2},
                name=CONFIG_LABELS.get(cid, cid),
            )
        )

    layout = _base_layout(
        "IR Quality vs Answer Quality per Config — Alignment = good; Divergence = bottleneck",
        "Cross-Lens",
    )
    layout.update(
        {
            "polar": {
                "radialaxis": {
                    "visible": True,
                    "range": [0, 1],
                    "tickfont": {"size": 10},
                    "gridcolor": _GRID_COLOR,
                },
                "angularaxis": {"tickfont": {"size": 11}},
                "bgcolor": _PLOT_BG,
            },
        }
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_radar_ir_vs_judge.html")


# ── Chart 6: Scatter — IR score vs Judge score ────────────────────────────────


def chart_scatter_ir_vs_judge(data: dict) -> None:
    """Scatter: x = avg MRR, y = avg judge score; one point per config."""
    active = _active_configs(data)
    rows = []
    for cid in active:
        config_data = data["configs"][cid]
        scores = config_data["scores"]
        rows.append(
            {
                "config": CONFIG_LABELS.get(cid, cid),
                "config_id": cid,
                "ir_score": scores.get("mrr", 0),
                "judge_score": config_data.get("judge_avg", 0),
                "ndcg": scores.get("ndcg_10", 0),
                "color": CONFIG_COLORS.get(cid, UN_BLUE),
            }
        )

    df = pd.DataFrame(rows)
    fig = px.scatter(
        df,
        x="ir_score",
        y="judge_score",
        color="config",
        size="ndcg",
        text="config",
        size_max=45,
        color_discrete_map={
            CONFIG_LABELS.get(cid, cid): CONFIG_COLORS.get(cid, UN_BLUE) for cid in active
        },
        labels={
            "ir_score": "Avg IR Score (MRR ↑ better)",
            "judge_score": "Avg LLM-as-Judge Score (1–5 ↑ better)",
            "config": "Config",
        },
    )
    fig.update_traces(textposition="top center", marker_line_color="white", marker_line_width=1.5)

    # Quadrant reference lines
    fig.add_vline(x=MRR_TARGET, line_dash="dash", line_color="#D55E00", line_width=1)
    fig.add_hline(y=PASS_THRESHOLD, line_dash="dash", line_color="#009E73", line_width=1)

    # Quadrant annotations
    fig.add_annotation(
        x=MRR_TARGET + 0.01,
        y=PASS_THRESHOLD + 0.1,
        text="✅ Both targets met",
        showarrow=False,
        font={"size": 10, "color": "#009E73"},
        xanchor="left",
    )
    fig.add_annotation(
        x=MRR_TARGET - 0.02,
        y=PASS_THRESHOLD - 0.2,
        text="⚠ Retrieval gap",
        showarrow=False,
        font={"size": 10, "color": "#D55E00"},
        xanchor="right",
    )

    layout = _base_layout(
        "IR Score vs Judge Score — Divergence flags where to optimise (retrieval vs generation)",
        "Cross-Lens",
    )
    layout.update(
        {
            "yaxis": {
                "range": [0, 5.5],
                "gridcolor": _GRID_COLOR,
                "title": "Avg LLM-as-Judge Score (1–5)",
            },
            "xaxis": {
                "range": [0, 1.05],
                "gridcolor": _GRID_COLOR,
                "title": "Avg IR Score — MRR (0–1)",
            },
        }
    )
    fig.add_annotation(
        text="Bubble size = nDCG@10",
        xref="paper",
        yref="paper",
        x=0.98,
        y=0.02,
        showarrow=False,
        font={"size": 11, "color": "#6B7280"},
    )
    fig.update_layout(**layout)
    _save(fig, "phase4_scatter_ir_vs_judge.html")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("Phase 4 Visualization — Policy Brief Generation")
    print("=" * 60)

    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found.")
        print("Run evaluate_phase4.py first.")
        sys.exit(1)

    with open(RESULTS_PATH) as f:
        data = json.load(f)

    active = _active_configs(data)
    print(f"Loaded results: {len(active)} active config(s) — {active}")
    print(f"Winner: {data.get('winner')}\n")

    print("Generating charts…")
    chart_ir_metrics(data)
    chart_ir_latency(data)
    chart_judge_quality(data)
    chart_judge_heatmap(data)
    chart_radar_ir_vs_judge(data)
    chart_scatter_ir_vs_judge(data)

    print(f"\n✅ All charts saved to {CHARTS_DIR}/")
    print("\nChart summary:")
    print("  [IR/RAG]       phase4_ir_metrics.html       — retrieval metrics bar chart")
    print("  [IR/RAG]       phase4_ir_latency.html        — IR score vs latency scatter")
    print("  [LLM-as-Judge] phase4_judge_quality.html     — answer quality bar chart")
    print("  [LLM-as-Judge] phase4_judge_heatmap.html     — per-question score heatmap")
    print("  [Cross-Lens]   phase4_radar_ir_vs_judge.html — IR vs Judge radar overlay")
    print("  [Cross-Lens]   phase4_scatter_ir_vs_judge.html — IR score vs Judge score")


if __name__ == "__main__":
    main()
