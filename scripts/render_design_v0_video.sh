#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

set +u
source /usr/lib/openfoam/openfoam2312/etc/bashrc
set -u
set -e

python3 scripts/design_v0_geometry.py
./cases/design_v0/Allrun
set +e
pvpython scripts/paraview_design_v0_render.py "$@"
pv_status=$?
set -e
if [[ "$pv_status" -ne 0 ]]; then
    if compgen -G "results/openfoam_design_v0/paraview/frames/frame_*.png" > /dev/null; then
        echo "pvpython exited with status $pv_status after writing frames; continuing to encode."
    else
        exit "$pv_status"
    fi
fi
python3 scripts/encode_paraview_frames.py

echo "Video: results/openfoam_design_v0/design_v0_paraview_orbit.mp4"
echo "Still: results/openfoam_design_v0/paraview/design_v0_potential_still.png"
