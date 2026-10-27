"""Pandas/NumPy data preparation and Matplotlib chart generation."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GENERATED_DIR = Path(__file__).resolve().parent / "static" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _frame(rows: list[dict], date_key: str | None = None, value_key: str | None = None) -> pd.DataFrame:
    """Normalize database rows and handle missing or non-numeric values."""
    frame = pd.DataFrame(rows or [])
    if date_key and date_key in frame:
        frame[date_key] = pd.to_datetime(frame[date_key], errors="coerce")
    if value_key and value_key in frame:
        frame[value_key] = pd.to_numeric(frame[value_key], errors="coerce").fillna(0)
    return frame


def _save_empty_chart(path: Path, title: str, message: str = "Complete a sale to see analytics") -> str:
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=120)
    ax.set_title(title, loc="left", fontweight="bold", pad=16)
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, color="#667085")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"/static/generated/{path.name}?v={int(path.stat().st_mtime)}"


def line_chart(rows: list[dict], title: str = "Revenue trend") -> str:
    path = GENERATED_DIR / "sales_trend.png"
    frame = _frame(rows, "sale_day", "revenue")
    if frame.empty or "sale_day" not in frame or "revenue" not in frame or frame["revenue"].sum() <= 0:
        return _save_empty_chart(path, title)
    frame = frame.dropna(subset=["sale_day"]).sort_values("sale_day")
    # NumPy is used for a compact numeric view of the trend.
    values = np.asarray(frame["revenue"].fillna(0), dtype=float)
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=120)
    ax.plot(frame["sale_day"], values, marker="o", linewidth=2.5, markersize=5, color="#3763f4")
    ax.fill_between(frame["sale_day"], values, alpha=0.10, color="#3763f4")
    ax.set_title(title, loc="left", fontweight="bold", pad=16)
    ax.set_ylabel("Revenue (₹)")
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.20)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"/static/generated/{path.name}?v={int(path.stat().st_mtime)}"


def category_chart(rows: list[dict]) -> str:
    path = GENERATED_DIR / "category_mix.png"
    frame = _frame(rows, value_key="revenue")
    if frame.empty or "revenue" not in frame or frame["revenue"].sum() <= 0:
        return _save_empty_chart(path, "Revenue by category")
    labels = frame.get("category_name", pd.Series(["Other"] * len(frame))).fillna("Other").astype(str)
    values = np.asarray(frame["revenue"], dtype=float)
    fig, ax = plt.subplots(figsize=(6, 3.6), dpi=120)
    ax.pie(values, labels=labels, autopct=lambda pct: f"{pct:.0f}%" if pct >= 5 else "", startangle=90,
           wedgeprops={"width": 0.42, "edgecolor": "white"}, textprops={"fontsize": 8})
    ax.set_title("Revenue by category", loc="left", fontweight="bold", pad=14)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"/static/generated/{path.name}?v={int(path.stat().st_mtime)}"


def branch_stock_chart(rows: list[dict]) -> str:
    path = GENERATED_DIR / "branch_stock.png"
    frame = _frame(rows, value_key="units")
    if frame.empty or "units" not in frame:
        return _save_empty_chart(path, "Stock by branch", "Add branches and products to compare stock")
    names = frame.get("branch_name", pd.Series(["Branch"] * len(frame))).fillna("Branch").astype(str)
    values = np.asarray(frame["units"], dtype=float)
    fig, ax = plt.subplots(figsize=(6, 3.6), dpi=120)
    ax.bar(names, values, color="#18a999", width=0.62)
    ax.set_title("Stock units by branch", loc="left", fontweight="bold", pad=14)
    ax.set_ylabel("Units")
    ax.grid(axis="y", alpha=0.20)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"/static/generated/{path.name}?v={int(path.stat().st_mtime)}"


def summary_stats(trend_rows: list[dict]) -> dict:
    frame = _frame(trend_rows, "sale_day", "revenue")
    values = np.asarray(frame["revenue"], dtype=float) if "revenue" in frame else np.asarray([], dtype=float)
    return {
        "tracked_days": int(values.size),
        "average_daily_revenue": float(np.mean(values)) if values.size else 0.0,
        "best_day_revenue": float(np.max(values)) if values.size else 0.0,
        "total_revenue": float(np.sum(values)) if values.size else 0.0,
    }
