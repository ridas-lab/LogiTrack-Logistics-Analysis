"""Create the Week 4 figures from saved modeling results.

The report figures use Matplotlib and Seaborn. This script never fits models,
selects a winner from test performance, trims prediction outcomes, or changes
the underlying result tables. Run model.py before this script.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter
import numpy as np
import pandas as pd
import seaborn as sns


NAVY = "#17354D"
TEAL = "#007F7F"
ORANGE = "#D97833"
GRAY = "#8A969E"
INK = "#15232D"


def theme() -> None:
    """Use legible figure typography and restrained grid lines."""
    sns.set_theme(style="whitegrid", context="notebook", font="DejaVu Sans")
    plt.rcParams.update({
        "font.size": 13,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12.5,
        "axes.titlecolor": "black",
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.labelsize": 11.5,
        "ytick.labelsize": 11.5,
        "legend.fontsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#9AA7AF",
        "grid.color": "#DDE3E7",
        "grid.linewidth": 0.7,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save(fig, output: Path, stem: str, description: str, manifest: list) -> None:
    """Save the same checked figure as an embedded PNG and a vector PDF."""
    output.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf"):
        fig.savefig(output / f"{stem}.{extension}", dpi=220, bbox_inches="tight")
    manifest.append({"file": f"{stem}.png", "description": description,
                     "libraries": ["matplotlib", "seaborn"]})
    plt.close(fig)


def footer(fig, text: str, y: float = 0.025) -> None:
    fig.text(0.015, y, text, ha="left", va="bottom", fontsize=10.5, color="#44515B")


def figure_one(results: Path, output: Path, manifest: list, summary: dict) -> None:
    comparison = pd.read_csv(results / "validation_model_comparison.csv")
    comparison = comparison.sort_values(["mae_days", "model"]).reset_index(drop=True)
    labels = comparison.model.str.replace("Gradient boosting leaves", "Gradient boosting", regex=False)
    labels = labels.str.replace("Decision tree depth", "Decision tree depth", regex=False)
    comparison["display_model"] = labels
    colors = {name: (TEAL if name == summary["selected_model"] else
                    GRAY if "baseline" in name else NAVY)
              for name in comparison.model}
    palette = {display: colors[name] for display, name in zip(labels, comparison.model)}
    fig, ax = plt.subplots(figsize=(10, 5.7))
    sns.barplot(data=comparison, x="mae_days", y="display_model", hue="display_model",
                palette=palette, legend=False, errorbar=None, ax=ax, saturation=1)
    for index, row in comparison.iterrows():
        ax.text(row.mae_days + .035, index, f"{row.mae_days:.3f}", va="center", fontsize=11)
    ax.set(xlabel="Mean absolute error in days   (lower is better)", ylabel="",
           xlim=(0, comparison.mae_days.max() * 1.16))
    ax.set_title("Model selection on mature validation data", pad=13)
    ax.grid(axis="y", visible=False)
    footer(fig, f"Validation n = {int(comparison.n.iloc[0]):,}. Teal marks the selected model. Test data were not used for selection.")
    fig.tight_layout(rect=(0, .07, 1, 1))
    save(fig, output, "01_validation_comparison",
         "Candidate model MAE on the same mature validation cohort; the lowest MAE determines selection.", manifest)


def figure_two(results: Path, output: Path, manifest: list, summary: dict) -> None:
    test = pd.read_csv(results / "test_predictions.csv")
    actual = test.remaining_delivery_days.to_numpy()
    prediction = test.prediction_days.to_numpy()
    residual = prediction - actual
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.5))
    extent_max = max(actual.max(), prediction.max()) * 1.04
    density = axes[0].hexbin(actual, prediction, gridsize=42, bins="log", mincnt=1,
                            cmap="viridis", linewidths=0, extent=(0, extent_max, 0, extent_max))
    axes[0].plot([0, extent_max], [0, extent_max], "--", color=ORANGE,
                 linewidth=1.5, label="Perfect prediction")
    axes[0].set(xlim=(0, extent_max), ylim=(0, extent_max), xlabel="Actual delivery duration (days)",
                ylabel="Predicted duration (days)", title="Actual versus predicted")
    axes[0].legend(loc="upper left", fontsize=9.5, frameon=True)
    cb = fig.colorbar(density, ax=axes[0], pad=.025, fraction=.05)
    cb.set_label("Orders per cell (log scale)", fontsize=10)
    cb.ax.tick_params(labelsize=9)
    sns.histplot(x=residual, bins=55, color=NAVY, edgecolor="white", linewidth=.5, ax=axes[1])
    axes[1].axvline(0, color=ORANGE, linestyle="--", linewidth=1.6)
    axes[1].set(yscale="log", xlabel="Residual in days (prediction minus actual)",
                ylabel="Number of orders (log scale)", title="Full residual distribution")
    axes[1].grid(axis="x", visible=False)
    fig.suptitle("Frozen model on the held out test set", fontsize=15, fontweight="bold", y=.995)
    selected = next(row for row in summary["test"] if row["model"] == "Selected model")
    footer(fig, f"n = {len(test):,} | MAE {selected['mae_days']:.2f} days | Bias {selected['bias_days']:+.2f} days\n"
               "All valid test deliveries are plotted. No upper clipping. Negative residuals mean underprediction.", y=.01)
    fig.tight_layout(rect=(0, .11, 1, .95))
    save(fig, output, "02_test_diagnostics",
         "Full-range test actual-versus-predicted density and residual histogram; all valid test outcomes retained.", manifest)


def figure_three(results: Path, output: Path, manifest: list, summary: dict) -> None:
    monthly = pd.read_csv(results / "monthly_test_metrics.csv").sort_values("month")
    states = pd.read_csv(results / "state_test_metrics.csv").sort_values("n", ascending=False).head(8)
    monthly["label"] = [f"{month}\n(n={int(n):,})" for month, n in zip(monthly.month, monthly.n)]
    states = states.copy()
    states["label"] = [f"{state}  (n={int(n):,})" for state, n in zip(states.state, states.n)]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.4), gridspec_kw={"width_ratios": [1, 1.25]})
    sns.barplot(data=monthly, x="label", y="mae_days", color=TEAL, saturation=1,
                errorbar=None, ax=axes[0])
    for index, row in enumerate(monthly.itertuples()):
        axes[0].text(index, row.mae_days + .08, f"{row.mae_days:.2f}", ha="center", fontsize=11)
    axes[0].set(xlabel="Approval month", ylabel="Mean absolute error (days)",
                title="Error by approval month", ylim=(0, monthly.mae_days.max() * 1.22))
    axes[0].grid(axis="x", visible=False)
    sns.barplot(data=states, x="mae_days", y="label", color=NAVY, saturation=1,
                errorbar=None, ax=axes[1])
    for index, row in enumerate(states.itertuples()):
        axes[1].text(row.mae_days + .05, index, f"{row.mae_days:.2f}", va="center", fontsize=11)
    axes[1].set(xlabel="Mean absolute error (days)", ylabel="",
                title="Eight states with most test orders", xlim=(0, states.mae_days.max() * 1.18))
    axes[1].grid(axis="y", visible=False)
    fig.suptitle("Error varies across test cohorts", fontsize=15, fontweight="bold", y=.995)
    footer(fig, "n denotes eligible completed deliveries. States are selected by sample count, not model error.")
    fig.tight_layout(rect=(0, .07, 1, .95), w_pad=2.5)
    save(fig, output, "03_cohort_errors",
         "Test MAE by approval month and eight largest state cohorts, with explicit sample counts.", manifest)


def figure_four(results: Path, output: Path, manifest: list, summary: dict) -> None:
    importance = pd.read_csv(results / "permutation_importance.csv")
    importance = importance.sort_values("mean_mae_increase_days", ascending=True)
    names = {"order_value_brl": "Order merchandise value", "freight_brl": "Freight charge",
             "item_count": "Item count", "seller_count": "Seller count", "total_weight_g": "Total item weight",
             "total_volume_cm3": "Total item volume", "promise_days": "Promised duration",
             "approval_wait_days": "Approval waiting time", "customer_state": "Destination state",
             "approval_weekday": "Approval weekday"}
    fig, ax = plt.subplots(figsize=(10, 5.6))
    positions = np.arange(len(importance))
    ax.barh(positions, importance.mean_mae_increase_days, color=TEAL, height=.66,
             xerr=importance.std_mae_increase_days, error_kw={"ecolor": NAVY, "capsize": 3, "elinewidth": 1.2})
    ax.set_yticks(positions, [names.get(value, value) for value in importance.feature_group])
    ax.axvline(0, color="#52616B", linewidth=1)
    ax.set(xlabel="Increase in validation MAE after shuffling (days)", ylabel="")
    ax.set_title("Grouped permutation importance on validation data", pad=14)
    ax.grid(axis="y", visible=False)
    footer(fig, f"Validation n = {summary['validation_selected']['n']:,}; 5 shuffles per group. Bars show means; whiskers show one SD.\n"
               "Importance describes model reliance, not a causal effect. Correlated features can share predictive information.", y=.01)
    fig.tight_layout(rect=(0, .1, 1, 1))
    save(fig, output, "04_validation_importance",
         "Grouped permutation importance measured as validation MAE increase, with variability across five shuffles.", manifest)


def figure_five(results: Path, output: Path, manifest: list, summary: dict) -> None:
    queue = pd.read_csv(results / "queue_metrics.csv")
    primary = queue.loc[queue.capacity.eq(100)].set_index("policy").loc[["Model priority", "FIFO"]].reset_index()
    colors = {"Model priority": TEAL, "FIFO": GRAY}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.6), gridspec_kw={"width_ratios": [.9, 1.2]})
    sns.barplot(data=primary, x="policy", y="late_capture_pct", hue="policy", palette=colors,
                legend=False, errorbar=None, saturation=1, ax=axes[0])
    for index, row in primary.iterrows():
        axes[0].text(index, row.late_capture_pct + 2, f"{row.late_capture_pct:.1f}%\n{row.selected_late:,} late orders",
                     ha="center", va="bottom", fontsize=10.5)
    axes[0].set(xlabel="", ylabel="Share of known late orders selected", ylim=(0, 100),
                title="Primary quota of 100 reviews per day")
    axes[0].yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    axes[0].grid(axis="x", visible=False)
    sns.lineplot(data=queue, x="capacity", y="late_capture_pct", hue="policy", style="policy",
                 palette=colors, markers=True, dashes=False, errorbar=None, linewidth=2.1,
                 markersize=8, ax=axes[1])
    axes[1].set(xlabel="Daily review quota (orders)", ylabel="Share of known late orders selected",
                ylim=(0, 100), xticks=[25, 50, 100, 150], title="Capacity sensitivity")
    axes[1].yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    axes[1].legend(title=None, loc="lower right")
    model_row = primary.iloc[0]
    fifo_row = primary.iloc[1]
    fig.suptitle("Retrospective prioritization at equal review capacity", fontsize=15, fontweight="bold", y=.995)
    footer(fig, f"At 100/day both policies select {int(model_row.selected):,} orders. Selected outcomes unknown: "
               f"model {int(model_row.selected_unknown):,}, FIFO {int(fifo_row.selected_unknown):,}.\n"
               f"Capture denominator = {int(model_row.total_late):,} known late orders. Selection identifies delays; it does not prove prevention.", y=.01)
    fig.tight_layout(rect=(0, .11, 1, .95), w_pad=2)
    save(fig, output, "05_review_allocation",
         "Model priority versus FIFO at equal daily quotas; measured capture of known late outcomes, not prevented delays.", manifest)


def figure_six(results: Path, output: Path, manifest: list, summary: dict) -> None:
    metrics = pd.read_csv(results / "synthetic_metrics.csv")
    test = pd.read_csv(results / "synthetic_test_predictions.csv")
    metrics["cohort"] = metrics["split"].map({"validation": "Validation", "test": "Test"})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.4), gridspec_kw={"width_ratios": [1, 1.05]})
    sns.barplot(data=metrics, x="cohort", y="mae_days", hue="model", order=["Validation", "Test"],
                hue_order=["Ridge alpha 1", "Median baseline"],
                palette={"Ridge alpha 1": TEAL, "Median baseline": GRAY},
                errorbar=None, saturation=1, ax=axes[0])
    axes[0].set(xlabel="Chronological holdout", ylabel="Mean absolute error (days)",
                title="Simulated delivery model error", ylim=(0, metrics.mae_days.max() * 1.4))
    axes[0].legend(title=None, loc="upper right", fontsize=10)
    axes[0].grid(axis="x", visible=False)
    for container in axes[0].containers:
        axes[0].bar_label(container, fmt="%.2f", padding=4, fontsize=11)
    sns.scatterplot(data=test, x="delivery_days", y="prediction_days", color=NAVY,
                    alpha=.36, s=18, linewidth=0, ax=axes[1])
    upper = max(test.delivery_days.max(), test.prediction_days.max()) * 1.04
    axes[1].plot([0, upper], [0, upper], color=ORANGE, linestyle="--", label="Perfect prediction")
    axes[1].set(xlabel="Actual simulated duration (days)", ylabel="Predicted duration (days)",
                title=f"Simulated test predictions  (n={len(test):,})", xlim=(0, upper), ylim=(0, upper))
    axes[1].legend(loc="upper left", fontsize=10)
    fig.suptitle("Separate hypothetical shipment experiment", fontsize=15, fontweight="bold", y=.995)
    counts = summary["synthetic"]["split_counts"]
    footer(fig, f"Synthetic rows only: train {counts['train']:,}, validation {counts['validation']:,}, test {counts['test']:,}. "
               "Ridge alpha 1 was fixed in advance.\nThese simulated results are not evidence of real-world delivery improvements.", y=.01)
    fig.tight_layout(rect=(0, .11, 1, .95), w_pad=2)
    save(fig, output, "06_synthetic_experiment",
         "Separate fixed-parameter Ridge experiment on explicitly simulated shipments; chronological validation and test scores.", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "figures")
    args = parser.parse_args()
    theme()
    # Figure functions read only the tables generated by model.py.
    manifest = []
    summary = json.loads((args.results / "summary.json").read_text(encoding="utf-8"))
    for figure in (figure_one, figure_two, figure_three, figure_four, figure_five, figure_six):
        figure(args.results, args.output, manifest, summary)
    (args.output / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Created {len(manifest)} figures as PNG and PDF using Matplotlib and Seaborn.")


if __name__ == "__main__":
    main()
