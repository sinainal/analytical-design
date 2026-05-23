#!/usr/bin/env pvpython
"""Render Design V1 ParaView trajectory files with a fixed camera."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from paraview.simple import (  # type: ignore
    ColorBy,
    CreateView,
    Delete,
    GetColorTransferFunction,
    OpenDataFile,
    Render,
    ResetSession,
    SaveScreenshot,
    Show,
)


ROOT = Path(__file__).resolve().parents[1]
PARAVIEW_DIR = ROOT / "results" / "openfoam_design_v1" / "paraview"
OUT_DIR = PARAVIEW_DIR / "render"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paraview-dir", type=Path, default=PARAVIEW_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=960)
    return parser.parse_args()


def configure_display(source, view):
    display = Show(source, view)
    display.Representation = "Surface"
    display.PointSize = 6
    display.LineWidth = 2
    try:
        ColorBy(display, ("POINTS", "class_id"))
        display.RescaleTransferFunctionToDataRange(True, False)
        lut = GetColorTransferFunction("class_id")
        lut.InterpretValuesAsCategories = 1
        lut.Annotations = ["0", "channel", "1", "live", "2", "dead"]
        lut.IndexedColors = [
            0.72, 0.72, 0.72,
            0.88, 0.18, 0.12,
            0.10, 0.40, 0.85,
        ]
    except Exception:
        display.DiffuseColor = [0.2, 0.2, 0.8]
    return display


def configure_view(width: int, height: int):
    view = CreateView("RenderView")
    view.ViewSize = [width, height]
    view.Background = [1.0, 1.0, 1.0]
    camera = view.GetActiveCamera()
    camera.SetFocalPoint(0.0, 0.0, 0.0)
    camera.SetPosition(0.0, 0.0, 0.0075)
    camera.SetViewUp(0.0, 1.0, 0.0)
    view.CameraParallelProjection = 1
    view.CameraParallelScale = 0.0022
    return view


def render_still(paraview_dir: Path, out_dir: Path, width: int, height: int) -> None:
    ResetSession()
    view = configure_view(width, height)
    source = OpenDataFile(str(paraview_dir / "best_case_trajectories.vtp"))
    configure_display(source, view)
    Render(view)
    SaveScreenshot(str(out_dir / "design_v1_best_trajectories_still.png"), view, ImageResolution=[width, height])


def render_animation(paraview_dir: Path, out_dir: Path, width: int, height: int) -> None:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_files = sorted((paraview_dir / "animation_frames").glob("frame_*.vtp"))
    if not frame_files:
        raise FileNotFoundError(paraview_dir / "animation_frames")

    ResetSession()
    view = configure_view(width, height)
    for i, frame_file in enumerate(frame_files):
        source = OpenDataFile(str(frame_file))
        configure_display(source, view)
        Render(view)
        SaveScreenshot(str(frames_dir / f"frame_{i:04d}.png"), view, ImageResolution=[width, height])
        Delete(source)


def main() -> int:
    args = parse_args()
    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    render_still(args.paraview_dir, args.out_dir, args.width, args.height)
    render_animation(args.paraview_dir, args.out_dir, args.width, args.height)
    print(f"Rendered Design V1 ParaView frames to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
