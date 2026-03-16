"""CLI entry point for genshin-damage-track."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="genshin-damage-track",
    help="Extract and track damage numbers from Genshin Impact video files.",
    no_args_is_help=True,
)


def _configure_logging(verbose: bool) -> None:
    """Set up logging for the pipeline.

    When *verbose* is ``True`` all ``genshin_damage_track`` loggers are set
    to ``DEBUG``; otherwise only ``INFO`` and above are printed.
    """
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(
        stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False),
    )
    handler.setFormatter(
        logging.Formatter("%(levelname)s [%(name)s] %(message)s"),
    )
    root = logging.getLogger("genshin_damage_track")
    root.setLevel(level)
    root.addHandler(handler)


@app.command()
def run(
    video: Annotated[Path, typer.Argument(help="Path to the video file (FHD, 60fps).")],
    fps: Annotated[float, typer.Option("--fps", help="Frames to sample per second.")] = 1.0,
    dps_interval: Annotated[
        int,
        typer.Option("--dps-interval", help="DPS averaging window in frames (default: 60)."),
    ] = 60,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write DPS results to this CSV file."),
    ] = None,
    plot: Annotated[bool, typer.Option("--plot", help="Generate a DPS graph.")] = False,
    plot_output: Annotated[
        Optional[Path],
        typer.Option("--plot-output", help="Save the graph to this file instead of showing it."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging for pipeline diagnostics."),
    ] = False,
    save_crops: Annotated[
        Optional[Path],
        typer.Option(
            "--save-crops",
            help="Save cropped ROI images to this directory for visual inspection.",
        ),
    ] = None,
) -> None:
    """Extract damage data from VIDEO and optionally output CSV / graph."""
    from genshin_damage_track.orchestrator import run_pipeline
    from genshin_damage_track.visualizer import plot_damage, write_csv

    _configure_logging(verbose)

    if not video.exists():
        typer.echo(f"Error: video file not found: {video}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Processing {video} at {fps} fps ...")
    result = run_pipeline(
        video, sample_rate=fps, dps_interval=dps_interval, save_crops_dir=save_crops,
    )
    typer.echo(f"Pattern detected: {result.pattern.value}")
    typer.echo(f"Frames processed: {len(result.frame_records)}")
    typer.echo(f"DPS records: {len(result.dps_records)}")

    # Print diagnostic summary for debugging
    valid_frames = sum(1 for r in result.frame_records if r.total_damage is not None)
    typer.echo(f"Frames with valid OCR: {valid_frames}/{len(result.frame_records)}")

    if output is not None:
        write_csv(result, output)
        typer.echo(f"CSV saved to {output}")

    if plot:
        plot_damage(result, output_path=plot_output, show=(plot_output is None))
        if plot_output is not None:
            typer.echo(f"Graph saved to {plot_output}")


if __name__ == "__main__":
    app()
