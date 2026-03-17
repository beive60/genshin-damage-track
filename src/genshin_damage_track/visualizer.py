"""visualizer — generate DPS graphs and CSV output."""
from __future__ import annotations

import csv
from pathlib import Path

from genshin_damage_track.models import ExtractionResult, RegionPattern


def write_csv(result: ExtractionResult, output_path: str | Path) -> None:
    """Write *result* to a CSV file at *output_path*.

    The CSV contains DPS records computed from the cumulative damage deltas.
    When the pattern is ``PER_CHARACTER`` and a party has been resolved,
    per-character columns are appended using the party member names
    (e.g. ``胡桃_damage``, ``胡桃_pct``).

    Parameters
    ----------
    result:
        Extraction result produced by the pipeline.
    output_path:
        Destination file path.  Parent directories must exist.
    """
    path = Path(output_path)
    party = result.party

    fieldnames = ["timestamp_sec", "dps", "delta_damage", "total_damage"]
    for name in party:
        fieldnames.extend([f"{name}_damage", f"{name}_pct"])

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in result.dps_records:
            row: dict[str, object] = {
                "timestamp_sec": rec.timestamp_sec,
                "dps": f"{rec.dps:.2f}" if rec.dps is not None else "",
                "delta_damage": rec.delta_damage if rec.delta_damage is not None else "",
                "total_damage": rec.total_damage if rec.total_damage is not None else "",
            }
            # Map characters by name
            char_map = {ch.name: ch for ch in rec.characters}
            for name in party:
                ch = char_map.get(name)
                if ch is not None:
                    row[f"{name}_damage"] = ch.damage
                    if rec.total_damage and rec.total_damage > 0:
                        row[f"{name}_pct"] = f"{ch.damage / rec.total_damage * 100:.1f}"
                    else:
                        row[f"{name}_pct"] = ""
                else:
                    row[f"{name}_damage"] = ""
                    row[f"{name}_pct"] = ""
            writer.writerow(row)


def plot_damage(
    result: ExtractionResult,
    output_path: str | Path | None = None,
    show: bool = False,
) -> None:
    """Generate a DPS time-series graph from *result*.

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

    dps_records = result.dps_records
    timestamps = [r.timestamp_sec for r in dps_records]
    dps_values = [
        r.dps if r.dps is not None else float("nan")
        for r in dps_records
    ]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(timestamps, dps_values, label="DPS", marker="o", linewidth=1.5)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("DPS (damage / sec)")
    ax.set_title(
        f"Genshin Impact — Short-term DPS (interval={result.dps_interval} frames)"
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)
