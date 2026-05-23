#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run_sim=1
if [[ "${1:-}" == "--skip-sim" ]]; then
    run_sim=0
    shift
fi

set +u
source /usr/lib/openfoam/openfoam2312/etc/bashrc
set -u
set -e

if [[ "$run_sim" -eq 1 ]]; then
    python3 scripts/design_v2_population_sim.py
fi

set +e
pvpython scripts/paraview_design_v2_render.py "$@"
pv_status=$?
set -e
if [[ "$pv_status" -ne 0 ]]; then
    if compgen -G "results/openfoam_design_v2/paraview/render/frames/frame_*.png" > /dev/null; then
        echo "pvpython exited with status $pv_status after writing frames; continuing to encode."
    else
        exit "$pv_status"
    fi
fi

python3 scripts/encode_paraview_frames.py \
    --frames-dir results/openfoam_design_v2/paraview/render/frames \
    --output results/openfoam_design_v2/paraview/design_v2_best_validation_paraview.mp4 \
    --fps 24

echo "Video: results/openfoam_design_v2/paraview/design_v2_best_validation_paraview.mp4"
echo "Still: results/openfoam_design_v2/paraview/render/design_v2_best_validation_trajectories_still.png"
