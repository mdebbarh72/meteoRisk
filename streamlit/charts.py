import matplotlib
matplotlib.use("Agg")  # headless-safe backend, avoids $DISPLAY errors in Docker

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

# Consistent color mapping for risk levels, used across every chart
RISK_COLORS = {
    "Low": "#2ca02c",       # green
    "Moderate": "#f1c40f",  # yellow
    "High": "#e67e22",      # orange
    "Critical": "#e74c3c",  # red
}
RISK_ORDER = ["Low", "Moderate", "High", "Critical"]


def _empty_fig(message="No data available", figsize=(10, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color="gray")
    ax.axis("off")
    return fig


def risk_by_city(df: pd.DataFrame):
    """Horizontal bar chart of average risk score by city, sorted, full-page sized."""
    if df.empty or "city_name" not in df.columns:
        return _empty_fig()

    avg_df = (
        df.groupby("city_name")["risk_score"]
        .mean()
        .reset_index()
        .sort_values("risk_score", ascending=True)  # ascending so largest ends up on top of barh
    )

    # Scale figure height to the number of cities so bars never feel squeezed
    height = max(5, 0.5 * len(avg_df) + 2)
    fig, ax = plt.subplots(figsize=(11, height))

    norm = mcolors.Normalize(vmin=avg_df["risk_score"].min(), vmax=avg_df["risk_score"].max())
    cmap = cm.get_cmap("Reds")
    bar_colors = [cmap(norm(v)) for v in avg_df["risk_score"]]

    bars = ax.barh(avg_df["city_name"], avg_df["risk_score"], color=bar_colors, edgecolor="white", height=0.65)

    for bar, value in zip(bars, avg_df["risk_score"]):
        ax.annotate(
            f"{value:.1f}",
            (bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(6, 0), textcoords="offset points",
            ha="left", va="center", fontsize=10,
        )

    ax.set_title("Average Risk Score by City", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("Average Risk Score")
    ax.set_ylabel("")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, avg_df["risk_score"].max() * 1.15)

    fig.tight_layout()
    return fig


def risk_heatmap(df: pd.DataFrame):
    """
    Heatmap of risk score by city (rows) x date (columns).

    Replaces the old spaghetti line chart: once there are more than a
    handful of cities, overlapping lines and a huge legend become hard to
    read. A heatmap scales much better and makes hotspots easy to scan.
    """
    if df.empty or "forecast_date" not in df.columns:
        return _empty_fig()

    pivot = df.pivot_table(index="city_name", columns="forecast_date", values="risk_score", aggfunc="mean")
    pivot = pivot.sort_index()

    width = max(9, 0.9 * pivot.shape[1] + 3)
    height = max(5, 0.55 * pivot.shape[0] + 2)
    fig, ax = plt.subplots(figsize=(width, height))

    im = ax.imshow(pivot.values, cmap="Reds", aspect="auto", vmin=0)

    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels([d.strftime("%b %d") for d in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)

    # Annotate each cell with its value, flipping text color for readability
    vmax = np.nanmax(pivot.values) if pivot.size else 1
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if pd.notna(val):
                color = "white" if val > vmax * 0.6 else "black"
                ax.text(j, i, f"{val:.0f}", ha="center", va="center", color=color, fontsize=8)

    ax.set_title("Risk Score Heatmap — City x Date", fontsize=15, fontweight="bold", pad=15)
    fig.colorbar(im, ax=ax, label="Risk Score", shrink=0.8)

    fig.tight_layout()
    return fig


def precipitation_vs_temperature(df: pd.DataFrame):
    """Bubble scatter of precipitation vs temperature, colored by risk level, sized by risk score, with two clear legends."""
    if df.empty:
        return _empty_fig()

    fig, ax = plt.subplots(figsize=(11, 7))

    min_size, max_size = 60, 500
    score_min, score_max = df["risk_score"].min(), df["risk_score"].max()
    if score_max > score_min:
        sizes = min_size + (df["risk_score"] - score_min) / (score_max - score_min) * (max_size - min_size)
    else:
        sizes = pd.Series((min_size + max_size) / 2, index=df.index)

    for level in RISK_ORDER:
        subset = df[df["risk_level"] == level]
        if subset.empty:
            continue
        ax.scatter(
            subset["temperature_max"],
            subset["precipitation_sum"],
            s=sizes.loc[subset.index],
            c=RISK_COLORS[level],
            label=level,
            alpha=0.75,
            edgecolor="white",
            linewidth=0.6,
        )

    ax.set_title("Temperature vs Precipitation", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("Max Temperature (°C)")
    ax.set_ylabel("Total Precipitation (mm)")
    ax.grid(True, alpha=0.25)

    color_legend = ax.legend(title="Risk Level", loc="upper left", fontsize=10, framealpha=0.9)
    ax.add_artist(color_legend)

    # Separate legend explaining bubble size, using neutral-colored proxy dots
    if score_max > score_min:
        size_values = [score_min, (score_min + score_max) / 2, score_max]
        size_handles = [
            plt.scatter([], [], s=min_size + (v - score_min) / (score_max - score_min) * (max_size - min_size),
                        color="gray", alpha=0.6, edgecolor="white")
            for v in size_values
        ]
        ax.legend(
            size_handles, [f"{v:.0f}" for v in size_values],
            title="Risk Score (bubble size)", loc="upper right", fontsize=9, framealpha=0.9,
        )

    fig.tight_layout()
    return fig


def risk_distribution_pie(df: pd.DataFrame):
    """Donut chart of the count/share of forecasts by risk level, full-page sized."""
    if df.empty or "risk_level" not in df.columns:
        return _empty_fig()

    counts = df["risk_level"].value_counts().reindex(RISK_ORDER).fillna(0)
    counts = counts[counts > 0]

    if counts.empty:
        return _empty_fig()

    labels = counts.index.tolist()
    values = counts.values
    colors = [RISK_COLORS[level] for level in labels]
    explode = [0.06 if level == "Critical" else 0.0 for level in labels]

    fig, ax = plt.subplots(figsize=(9, 8))

    wedges, _, _ = ax.pie(
        values,
        colors=colors,
        explode=explode,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 0 else "",
        pctdistance=0.8,
        startangle=90,
        wedgeprops=dict(width=0.4, edgecolor="white"),
        textprops=dict(color="white", fontsize=11, fontweight="bold"),
    )

    ax.axis("equal")
    ax.set_title("Forecast Distribution by Risk Level", fontsize=15, fontweight="bold", pad=15)

    legend_labels = [f"{level} ({int(count)})" for level, count in zip(labels, values)]
    ax.legend(
        wedges, legend_labels, title="Risk Level",
        loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=len(labels), fontsize=10,
    )

    fig.tight_layout()
    return fig


def risk_score_spread(df: pd.DataFrame):
    """
    Boxplot of risk score spread per risk level.

    New stat, not just a restyle: shows the underlying distribution/variance
    of risk scores within each bucket, not just an average or a count — e.g.
    it reveals if "Moderate" is a tight, consistent band or a wide spread
    that's almost bleeding into "High".
    """
    if df.empty or "risk_score" not in df.columns:
        return _empty_fig()

    present_levels = [lvl for lvl in RISK_ORDER if lvl in df["risk_level"].unique()]
    data = [df.loc[df["risk_level"] == lvl, "risk_score"].values for lvl in present_levels]

    fig, ax = plt.subplots(figsize=(9, 7))

    bp = ax.boxplot(
        data, labels=present_levels, patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5),
        widths=0.5,
    )
    for patch, level in zip(bp["boxes"], present_levels):
        patch.set_facecolor(RISK_COLORS[level])
        patch.set_alpha(0.75)

    # Overlay individual points with slight jitter for a sense of sample size
    rng = np.random.default_rng(42)
    for i, lvl in enumerate(present_levels, start=1):
        vals = df.loc[df["risk_level"] == lvl, "risk_score"].values
        jitter = rng.uniform(-0.08, 0.08, size=len(vals))
        ax.scatter(np.full(len(vals), i) + jitter, vals, color="black", alpha=0.3, s=15, zorder=3)

    ax.set_title("Risk Score Distribution by Risk Level", fontsize=15, fontweight="bold", pad=15)
    ax.set_ylabel("Risk Score")
    ax.grid(True, axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    return fig