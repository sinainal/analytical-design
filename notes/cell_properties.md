# Cell Properties for Design V0

Date: 2026-05-23

## Purpose

This table defines the first live/dead mammalian cell model used for the V0 Clausius-Mossotti scan and later spiral DEP simulations.

The first model is intentionally near-equal in size so that any separation result cannot be explained purely by particle diameter.

## Reference Model

Primary source: `R5` in `reference_knowledge_base.md`.

| Property | Live U937-like cell | Dead U937-like cell | Notes |
|---|---:|---:|---|
| diameter | `23 um` | `22 um` | Near-equal sizes. |
| radius | `11.5 um` | `11.0 um` | Used in DEP force scaling. |
| membrane thickness | `7 nm` | `7 nm` | Single-shell model input. |
| membrane relative permittivity | `12.5` | `12.5` | Relative to vacuum permittivity. |
| membrane conductivity | `1e-6 S/m` | `0.01 S/m` | Dead membrane conductivity is much higher. |
| cytoplasm relative permittivity | `50` | `80` | Relative to vacuum permittivity. |
| cytoplasm conductivity | `0.5 S/m` | `0.002 S/m` | Literature-seeded first model. |
| medium relative permittivity | `80` | `80` | Low-conductivity aqueous DEP buffer. |
| medium conductivity | `0.002 S/m` | `0.002 S/m` | Same medium for both cells. |

## Modeling Choice

Use a single-shell effective complex permittivity model:

```text
epsilon_cell_eff =
    Cmem* * r * epsilon_int* / (Cmem* * r + epsilon_int*)

Cmem* = epsilon_mem* / membrane_thickness
epsilon* = epsilon0 * epsilon_r - j sigma / omega

CM = (epsilon_cell_eff - epsilon_medium*) /
     (epsilon_cell_eff + 2 epsilon_medium*)
```

This is a compact approximation for a shelled spherical cell. It is enough for the first frequency-selection scan, but the exact formulation should be revisited before publication-grade claims.

## First Selection Rule

Scan `1 kHz` to `10 MHz`.

Preferred frequency:

- live and dead `Re(CM)` have opposite signs; or
- absolute separation `abs(Re(CM_live) - Re(CM_dead))` is large.

The selected frequency should then be used in `design_v0` particle simulations.
