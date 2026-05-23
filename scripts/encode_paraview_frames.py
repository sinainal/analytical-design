#!/usr/bin/env python3
"""Encode ParaView PNG frames into an MP4 video."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRAMES = ROOT / "results" / "openfoam_design_v0" / "paraview" / "frames"
DEFAULT_VIDEO = ROOT / "results" / "openfoam_design_v0" / "design_v0_paraview_orbit.mp4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES)
    parser.add_argument("--output", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--fps", type=float, default=24.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frames = sorted(args.frames_dir.glob("frame_*.png"))
    if not frames:
        raise FileNotFoundError(f"No frames found in {args.frames_dir}")

    first = cv2.imread(str(frames[0]))
    if first is None:
        raise RuntimeError(f"Could not read first frame: {frames[0]}")
    height, width = first.shape[:2]
    args.output.parent.mkdir(parents=True, exist_ok=True)

    writer = cv2.VideoWriter(
        str(args.output),
        cv2.VideoWriter_fourcc(*"mp4v"),
        args.fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {args.output}")

    try:
        for frame_path in frames:
            frame = cv2.imread(str(frame_path))
            if frame is None:
                raise RuntimeError(f"Could not read frame: {frame_path}")
            writer.write(frame)
    finally:
        writer.release()

    print(f"Encoded {len(frames)} frames to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
