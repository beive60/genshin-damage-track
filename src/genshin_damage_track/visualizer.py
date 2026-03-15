"""visualizer — generate damage graphs and CSV output."""
from __future__ import annotations

import csv
from pathlib import Path

from genshin_damage_track.models import ExtractionResult, RegionPattern


def write_csv(result: ExtractionResult, output_path: str | Path) -> None:
    """Write *result* to a CSV file at *output_path*.

    Parameters
    ----------
    result:
        Extraction result produced by the pipeline.
    output_path:
        Destination file path.  Parent directories must exist.
    """
    path = Path(output_path)
    fieldnames = ["timestamp_sec", "party_damage", "individual_damage", "character_name"]

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in result.records:
            writer.writerow({
                "timestamp_sec": rec.timestamp_sec,
                "party_damage": rec.party_damage if rec.party_damage is not None else "",
                "individual_damage": rec.individual_damage if rec.individual_damage is not None else "",
                "character_name": rec.character_name if rec.character_name is not None else "",
            })


def plot_damage(
    result: ExtractionResult,
    output_path: str | Path | None = None,
    show: bool = False,
) -> None:
    """Generate a time-series damage graph from *result*.

    Parameters
    ----------
    result:
        Extraction result produced by the pipeline.
    output_path:
        When provided the graph is saved to this path (PNG/SVG/etc.).
    show:
        When ``True`` the graph is shown interactively via
        ``matplotlib.pyplot.show()``.
    """
    import matplotlib.pyplot as plt  # noqa: PLC0415

    timestamps = [r.timestamp_sec for r in result.records]

    party = [
        float(r.party_damage) if r.party_damage is not None else float("nan")
        for r in result.records
    ]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(timestamps, party, label="Party Damage", marker="o", linewidth=1.5)

    if result.pattern == RegionPattern.PATTERN_2:
        individual = [
            float(r.individual_damage) if r.individual_damage is not None else float("nan")
            for r in result.records
        ]
        ax.plot(timestamps, individual, label="Individual Damage", marker="s", linewidth=1.5)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Damage")
    ax.set_title("Genshin Impact — Damage over Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)
