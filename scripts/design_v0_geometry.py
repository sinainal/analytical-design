#!/usr/bin/env python3
"""Generate the first OpenFOAM-ready Archimedean spiral DEP case."""

from __future__ import annotations

import argparse
import math
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases" / "design_v0"


@dataclass(frozen=True)
class SpiralSpec:
    turns: float = 3.0
    inner_radius_m: float = 1000e-6
    channel_width_m: float = 120e-6
    channel_height_m: float = 50e-6
    pitch_m: float = 180e-6
    cells_along: int = 240
    cells_width: int = 8
    cells_height: int = 2
    voltage_v: float = 8.0
    inlet_velocity_m_s: float = 1000e-6


def foam_header(class_name: str, object_name: str) -> str:
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| Analytical Design: generated OpenFOAM file                                  |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {class_name};
    object      {object_name};
}}
// ************************************************************************* //
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def centerline(spec: SpiralSpec, i: int) -> tuple[float, float]:
    theta = 2.0 * math.pi * spec.turns * i / spec.cells_along
    b = spec.pitch_m / (2.0 * math.pi)
    radius = spec.inner_radius_m + b * theta
    return radius * math.cos(theta), radius * math.sin(theta)


def point_xyz(spec: SpiralSpec, i: int, j: int, k: int) -> tuple[float, float, float]:
    x, y = centerline(spec, i)

    if i == 0:
        xn, yn = centerline(spec, i + 1)
        xp, yp = x, y
    elif i == spec.cells_along:
        xp, yp = centerline(spec, i - 1)
        xn, yn = x, y
    else:
        xp, yp = centerline(spec, i - 1)
        xn, yn = centerline(spec, i + 1)

    tx, ty = xn - xp, yn - yp
    norm = math.hypot(tx, ty)
    tx, ty = tx / norm, ty / norm
    nx, ny = -ty, tx

    offset = -0.5 * spec.channel_width_m + spec.channel_width_m * j / spec.cells_width
    z = spec.channel_height_m * k / spec.cells_height
    return x + offset * nx, y + offset * ny, z


def point_id(spec: SpiralSpec, i: int, j: int, k: int) -> int:
    return (i * (spec.cells_width + 1) + j) * (spec.cells_height + 1) + k


def cell_vertices(spec: SpiralSpec, i: int, j: int, k: int) -> tuple[int, ...]:
    p000 = point_id(spec, i, j, k)
    p100 = point_id(spec, i + 1, j, k)
    p110 = point_id(spec, i + 1, j + 1, k)
    p010 = point_id(spec, i, j + 1, k)
    p001 = point_id(spec, i, j, k + 1)
    p101 = point_id(spec, i + 1, j, k + 1)
    p111 = point_id(spec, i + 1, j + 1, k + 1)
    p011 = point_id(spec, i, j + 1, k + 1)
    return p000, p100, p110, p010, p001, p101, p111, p011


def hexa_faces(vertices: tuple[int, ...]) -> list[tuple[int, int, int, int]]:
    p000, p100, p110, p010, p001, p101, p111, p011 = vertices
    return [
        (p000, p010, p110, p100),  # bottom
        (p001, p101, p111, p011),  # top
        (p000, p100, p101, p001),  # inner wall
        (p010, p011, p111, p110),  # outer wall
        (p000, p001, p011, p010),  # inlet-side
        (p100, p110, p111, p101),  # outlet-side
    ]


def build_mesh(spec: SpiralSpec) -> tuple[list[tuple[float, float, float]], list[dict]]:
    points = [
        point_xyz(spec, i, j, k)
        for i in range(spec.cells_along + 1)
        for j in range(spec.cells_width + 1)
        for k in range(spec.cells_height + 1)
    ]
    cells = []
    for i in range(spec.cells_along):
        for j in range(spec.cells_width):
            for k in range(spec.cells_height):
                cells.append({"ijk": (i, j, k), "vertices": cell_vertices(spec, i, j, k)})
    return points, cells


def classify_boundary(spec: SpiralSpec, face: tuple[int, ...], owner_ijk: tuple[int, int, int]) -> str:
    i, j, k = owner_ijk
    ids = set(face)
    if ids == {point_id(spec, 0, j, k), point_id(spec, 0, j, k + 1), point_id(spec, 0, j + 1, k + 1), point_id(spec, 0, j + 1, k)}:
        return "inlet"
    if ids == {
        point_id(spec, spec.cells_along, j, k),
        point_id(spec, spec.cells_along, j + 1, k),
        point_id(spec, spec.cells_along, j + 1, k + 1),
        point_id(spec, spec.cells_along, j, k + 1),
    }:
        midpoint_j = j + 0.5
        return "outlet_inner" if midpoint_j < spec.cells_width / 2.0 else "outlet_outer"
    if j == 0 and ids == {
        point_id(spec, i, 0, k),
        point_id(spec, i + 1, 0, k),
        point_id(spec, i + 1, 0, k + 1),
        point_id(spec, i, 0, k + 1),
    }:
        return "inner_electrode"
    if j == spec.cells_width - 1 and ids == {
        point_id(spec, i, spec.cells_width, k),
        point_id(spec, i, spec.cells_width, k + 1),
        point_id(spec, i + 1, spec.cells_width, k + 1),
        point_id(spec, i + 1, spec.cells_width, k),
    }:
        return "outer_electrode"
    if k == 0:
        return "bottom_wall"
    if k == spec.cells_height - 1:
        return "top_wall"
    raise ValueError(f"Unclassified boundary face {face} for cell {owner_ijk}")


def build_faces(spec: SpiralSpec, cells: list[dict]) -> tuple[list[tuple[int, ...]], list[int], list[int], dict[str, list[int]]]:
    face_map: dict[tuple[int, ...], int] = {}
    face_data: list[dict] = []

    for cell_id, cell in enumerate(cells):
        for face in hexa_faces(cell["vertices"]):
            key = tuple(sorted(face))
            if key in face_map:
                face_data[face_map[key]]["neighbour"] = cell_id
            else:
                face_map[key] = len(face_data)
                face_data.append({"face": face, "owner": cell_id, "neighbour": None, "owner_ijk": cell["ijk"]})

    patch_order = [
        "inlet",
        "outlet_inner",
        "outlet_outer",
        "inner_electrode",
        "outer_electrode",
        "top_wall",
        "bottom_wall",
    ]
    internal = [item for item in face_data if item["neighbour"] is not None]
    boundary_by_patch: dict[str, list[dict]] = {name: [] for name in patch_order}
    for item in face_data:
        if item["neighbour"] is None:
            patch = classify_boundary(spec, item["face"], item["owner_ijk"])
            boundary_by_patch[patch].append(item)

    boundary = [item for name in patch_order for item in boundary_by_patch[name]]
    ordered = internal + boundary

    faces = [item["face"] for item in ordered]
    owners = [item["owner"] for item in ordered]
    neighbours = [item["neighbour"] for item in internal]
    patches: dict[str, list[int]] = {}
    start = len(internal)
    for name in patch_order:
        n_faces = len(boundary_by_patch[name])
        patches[name] = list(range(start, start + n_faces))
        start += n_faces

    return faces, owners, neighbours, patches


def write_list(path: Path, header_class: str, object_name: str, values: list[str]) -> None:
    body = "\n".join(values)
    write_text(path, f"{foam_header(header_class, object_name)}\n{len(values)}\n(\n{body}\n)\n")


def write_polymesh(case_dir: Path, spec: SpiralSpec) -> None:
    points, cells = build_mesh(spec)
    faces, owners, neighbours, patches = build_faces(spec, cells)
    mesh_dir = case_dir / "constant" / "polyMesh"
    shutil.rmtree(mesh_dir, ignore_errors=True)
    mesh_dir.mkdir(parents=True, exist_ok=True)

    write_list(
        mesh_dir / "points",
        "vectorField",
        "points",
        [f"({x:.12g} {y:.12g} {z:.12g})" for x, y, z in points],
    )
    write_list(
        mesh_dir / "faces",
        "faceList",
        "faces",
        [f"4({' '.join(str(v) for v in face)})" for face in faces],
    )
    write_list(mesh_dir / "owner", "labelList", "owner", [str(v) for v in owners])
    write_list(mesh_dir / "neighbour", "labelList", "neighbour", [str(v) for v in neighbours])

    patch_order = [
        "inlet",
        "outlet_inner",
        "outlet_outer",
        "inner_electrode",
        "outer_electrode",
        "top_wall",
        "bottom_wall",
    ]
    start = len(neighbours)
    boundary_lines = [str(len(patch_order)), "("]
    for name in patch_order:
        n_faces = len(patches[name])
        if not all(index == start + n for n, index in enumerate(patches[name])):
            raise RuntimeError(f"Patch faces for {name} are not contiguous")
        patch_type = "patch" if name in {"inlet", "outlet_inner", "outlet_outer"} else "wall"
        boundary_lines.extend(
            [
                f"    {name}",
                "    {",
                f"        type            {patch_type};",
                f"        nFaces          {n_faces};",
                f"        startFace       {start};",
                "    }",
            ]
        )
        start += n_faces
    boundary_lines.append(")")
    write_text(mesh_dir / "boundary", foam_header("polyBoundaryMesh", "boundary") + "\n".join(boundary_lines) + "\n")


def write_field_files(case_dir: Path, spec: SpiralSpec) -> None:
    inlet_u = f"({spec.inlet_velocity_m_s:.8g} 0 0)"
    write_text(
        case_dir / "0" / "U",
        foam_header("volVectorField", "U")
        + f"""
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform {inlet_u};
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {inlet_u};
    }}
    outlet_inner {{ type zeroGradient; }}
    outlet_outer {{ type zeroGradient; }}
    inner_electrode {{ type noSlip; }}
    outer_electrode {{ type noSlip; }}
    top_wall {{ type noSlip; }}
    bottom_wall {{ type noSlip; }}
}}
""",
    )
    write_text(
        case_dir / "0" / "p",
        foam_header("volScalarField", "p")
        + """
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet { type zeroGradient; }
    outlet_inner { type fixedValue; value uniform 0; }
    outlet_outer { type fixedValue; value uniform 0; }
    inner_electrode { type zeroGradient; }
    outer_electrode { type zeroGradient; }
    top_wall { type zeroGradient; }
    bottom_wall { type zeroGradient; }
}
""",
    )
    write_text(
        case_dir / "0" / "phiE",
        foam_header("volScalarField", "phiE")
        + f"""
dimensions      [1 2 -3 0 0 -1 0];
internalField   uniform 0;
boundaryField
{{
    inlet {{ type zeroGradient; }}
    outlet_inner {{ type zeroGradient; }}
    outlet_outer {{ type zeroGradient; }}
    inner_electrode {{ type fixedValue; value uniform {spec.voltage_v:.8g}; }}
    outer_electrode {{ type fixedValue; value uniform 0; }}
    top_wall {{ type zeroGradient; }}
    bottom_wall {{ type zeroGradient; }}
}}
""",
    )
    write_text(
        case_dir / "0" / "T",
        foam_header("volScalarField", "T")
        + f"""
dimensions      [0 0 0 0 0 0 0];
internalField   uniform 0;
boundaryField
{{
    inlet {{ type zeroGradient; }}
    outlet_inner {{ type zeroGradient; }}
    outlet_outer {{ type zeroGradient; }}
    inner_electrode {{ type fixedValue; value uniform {spec.voltage_v:.8g}; }}
    outer_electrode {{ type fixedValue; value uniform 0; }}
    top_wall {{ type zeroGradient; }}
    bottom_wall {{ type zeroGradient; }}
}}
""",
    )


def write_system(case_dir: Path) -> None:
    write_text(
        case_dir / "system" / "controlDict",
        foam_header("dictionary", "controlDict")
        + """
application     laplacianFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""",
    )
    write_text(
        case_dir / "system" / "fvSchemes",
        foam_header("dictionary", "fvSchemes")
        + """
ddtSchemes { default Euler; }
gradSchemes
{
    default none;
    grad(T) Gauss linear;
    grad(U) Gauss linear;
}
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default Gauss linear corrected;
    laplacian(DT,T) Gauss linear corrected;
}
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
""",
    )
    write_text(
        case_dir / "system" / "fvSolution",
        foam_header("dictionary", "fvSolution")
        + """
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-8;
        relTol          0.01;
        smoother        GaussSeidel;
    }
    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }
    phiE
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-10;
        relTol          0;
    }
    T
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-10;
        relTol          0;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 2;
    consistent yes;
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; }
}
""",
    )


def write_constant(case_dir: Path) -> None:
    write_text(
        case_dir / "constant" / "transportProperties",
        foam_header("dictionary", "transportProperties")
        + """
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 1e-06;
DT              1;
""",
    )


def write_run_files(case_dir: Path) -> None:
    write_text(
        case_dir / "README.md",
        """# Design V0 OpenFOAM Case

Generated by `scripts/design_v0_geometry.py`.

This is the first Archimedean spiral DEP OpenFOAM case. It contains a direct
`polyMesh`, initial flow/electric-potential fields, and minimal solver
dictionaries for mesh validation and later field solving.

Baseline geometry:

- turns: 3
- inner radius: 1000 um
- width: 120 um
- height: 50 um
- pitch: 180 um
- inlet velocity: 1000 um/s
- inner electrode: 8 V
- outer electrode: 0 V

Current status: geometry/mesh case only. Particle tracking and electric-field
post-processing are the next layer. The `T` field is used as the first
OpenFOAM Laplace potential proxy so `laplacianFoam` can validate the electrode
boundary condition before a custom `phiE` workflow is added.
""",
    )
    write_text(
        case_dir / "Allcheck",
        """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
checkMesh | tee log.checkMesh
touch design_v0.foam
""",
    )
    (case_dir / "Allcheck").chmod(0o755)
    write_text(
        case_dir / "Allrun",
        """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
checkMesh | tee log.checkMesh
laplacianFoam | tee log.laplacianFoam
touch design_v0.foam
""",
    )
    (case_dir / "Allrun").chmod(0o755)
    write_text(case_dir / "design_v0.foam", "")


def write_metadata(case_dir: Path, spec: SpiralSpec) -> None:
    write_text(
        case_dir / "case_parameters.json",
        f"""{{
  "turns": {spec.turns},
  "inner_radius_m": {spec.inner_radius_m},
  "channel_width_m": {spec.channel_width_m},
  "channel_height_m": {spec.channel_height_m},
  "pitch_m": {spec.pitch_m},
  "cells_along": {spec.cells_along},
  "cells_width": {spec.cells_width},
  "cells_height": {spec.cells_height},
  "voltage_v": {spec.voltage_v},
  "inlet_velocity_m_s": {spec.inlet_velocity_m_s},
  "selected_frequency_hz": 455326
}}
""",
    )


def generate(case_dir: Path, spec: SpiralSpec) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    for path in case_dir.iterdir():
        if path.is_dir() and path.name.isdigit() and path.name != "0":
            shutil.rmtree(path)
        elif path.is_dir() and path.name in {"postProcessing", "VTK"}:
            shutil.rmtree(path)
        elif path.is_file() and path.name.startswith("log."):
            path.unlink()
    for child in ["0", "constant", "system"]:
        (case_dir / child).mkdir(parents=True, exist_ok=True)
    write_polymesh(case_dir, spec)
    write_field_files(case_dir, spec)
    write_constant(case_dir)
    write_system(case_dir)
    write_run_files(case_dir)
    write_metadata(case_dir, spec)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, default=CASE_DIR)
    parser.add_argument("--turns", type=float, default=3.0)
    parser.add_argument("--cells-along", type=int, default=240)
    parser.add_argument("--cells-width", type=int, default=8)
    parser.add_argument("--cells-height", type=int, default=2)
    parser.add_argument("--voltage", type=float, default=8.0)
    parser.add_argument("--velocity", type=float, default=1000e-6)
    args = parser.parse_args()

    spec = SpiralSpec(
        turns=args.turns,
        cells_along=args.cells_along,
        cells_width=args.cells_width,
        cells_height=args.cells_height,
        voltage_v=args.voltage,
        inlet_velocity_m_s=args.velocity,
    )
    generate(args.case_dir, spec)
    print(f"Generated OpenFOAM design_v0 case: {args.case_dir}")
    print(f"Cells: {spec.cells_along * spec.cells_width * spec.cells_height}")
    print("Run: source /usr/lib/openfoam/openfoam2312/etc/bashrc && cases/design_v0/Allcheck")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
