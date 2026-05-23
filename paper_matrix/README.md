# Paper Matrix

This matrix classifies collected papers by three binary axes:

- `S`: spiral channel or spiral electrode/channel concept
- `D`: dielectrophoresis
- `T`: dead/live, viable/nonviable, or dead-cell topic

Folder naming:

```text
S{0|1}_D{0|1}_T{0|1}
```

Examples:

- `S1_D0_T1`: spiral is used, DEP is not used, dead/nonviable-cell topic is present.
- `S0_D1_T1`: no spiral, DEP is used, dead/live topic is present.
- `S1_D1_T1`: spiral + DEP + dead/live topic. This is the target combination.

Important: `S1_D1_T1` currently contains proxy papers, not a confirmed direct match. This folder documents the gap by placing the nearest papers from each neighboring category together.
