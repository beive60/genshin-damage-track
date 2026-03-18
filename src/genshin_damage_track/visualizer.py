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
        fieldnames.extend([f"{name}_damage", f"{name}_dps", f"{name}_pct"])

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
                        pct = ch.damage / rec.total_damage
                        row[f"{name}_pct"] = f"{pct * 100:.1f}"
                        row[f"{name}_dps"] = f"{rec.dps * pct:.2f}" if rec.dps is not None else ""
                    else:
                        row[f"{name}_pct"] = ""
                        row[f"{name}_dps"] = ""
                else:
                    row[f"{name}_damage"] = ""
                    row[f"{name}_dps"] = ""
                    row[f"{name}_pct"] = ""
            writer.writerow(row)


def plot_damage(
    result: ExtractionResult,
    output_path: str | Path | None = None,
    show: bool = False,
) -> None:
    """Generate DPS and total-damage time-series graphs from *result*.

    Two subplots are produced:

    1. **DPS** — overall DPS line.  When the pattern is
       ``PER_CHARACTER`` and a party has been resolved, per-character
       DPS lines are drawn as well.
    2. **Total damage** — cumulative damage over time.

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
    import matplotlib.ticker as ticker  # noqa: PLC0415

    dps_records = result.dps_records
    timestamps = [r.timestamp_sec for r in dps_records]
    dps_values = [
        r.dps if r.dps is not None else float("nan")
        for r in dps_records
    ]
    total_damage_values = [
        r.total_damage if r.total_damage is not None else float("nan")
        for r in dps_records
    ]

    fig, (ax_dps, ax_dmg) = plt.subplots(2, 1, figsize=(12, 9))

    # --- DPS subplot ---
    ax_dps.plot(timestamps, dps_values, label="DPS", marker="o", linewidth=1.5)

    if result.pattern == RegionPattern.PER_CHARACTER and result.party:
        for name in result.party:
            char_dps = []
            for rec in dps_records:
                char_map = {ch.name: ch for ch in rec.characters}
                ch = char_map.get(name)
                if ch is not None and rec.dps is not None and rec.total_damage and rec.total_damage > 0:
                    pct = ch.damage / rec.total_damage
                    char_dps.append(rec.dps * pct)
                else:
                    char_dps.append(float("nan"))
            ax_dps.plot(timestamps, char_dps, label=name, linewidth=1.0)

    ax_dps.set_xlabel("Time (s)")
    ax_dps.set_ylabel("DPS (×1000 damage / sec)")
    ax_dps.set_title(
        f"Genshin Impact — Short-term DPS (interval={result.dps_interval} frames)"
    )
    ax_dps.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x / 1e3:.1f}"))
    ax_dps.legend()
    ax_dps.grid(True, alpha=0.3)

    # --- Total damage subplot ---
    ax_dmg.plot(timestamps, total_damage_values, label="Total Damage", marker="o", linewidth=1.5, color="tab:green")
    ax_dmg.set_xlabel("Time (s)")
    ax_dmg.set_ylabel("Total Damage (×1000)")
    ax_dmg.set_title(
        f"Genshin Impact — Cumulative Total Damage (interval={result.dps_interval} frames)"
    )
    ax_dmg.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x / 1e3:.1f}"))
    ax_dmg.legend()
    ax_dmg.grid(True, alpha=0.3)

    fig.tight_layout()

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)
