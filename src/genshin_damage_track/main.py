"""CLI entry point for genshin-damage-track."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

app = typer.Typer(
    name="genshin-damage-track",
    help="Extract and track damage numbers from Genshin Impact video files.",
    no_args_is_help=True,
)


@app.command()
def run(
    video: Annotated[Path, typer.Argument(help="Path to the video file (FHD, 60fps).")],
    fps: Annotated[float, typer.Option("--fps", help="Frames to sample per second.")] = 1.0,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write results to this CSV file."),
    ] = None,
    plot: Annotated[bool, typer.Option("--plot", help="Generate a damage graph.")] = False,
    plot_output: Annotated[
        Optional[Path],
        typer.Option("--plot-output", help="Save the graph to this file instead of showing it."),
    ] = None,
) -> None:
    """Extract damage data from VIDEO and optionally output CSV / graph."""
    from genshin_damage_track.orchestrator import run_pipeline
    from genshin_damage_track.visualizer import plot_damage, write_csv

    if not video.exists():
        typer.echo(f"Error: video file not found: {video}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Processing {video} at {fps} fps …")
    result = run_pipeline(video, sample_rate=fps)
    typer.echo(f"Pattern detected: {result.pattern.value}")
    typer.echo(f"Frames processed: {len(result.records)}")

    if output is not None:
        write_csv(result, output)
        typer.echo(f"CSV saved to {output}")

    if plot:
        plot_damage(result, output_path=plot_output, show=(plot_output is None))
        if plot_output is not None:
            typer.echo(f"Graph saved to {plot_output}")


if __name__ == "__main__":
    app()
