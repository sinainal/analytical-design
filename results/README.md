# Results Directory

This directory contains generated project outputs that are useful for design
decisions and later manuscript figures.

## Structure

| Directory | Purpose | Versioned |
|---|---|---|
| `cm_factor/` | First analytical live/dead DEP frequency scan. | Yes |
| `raw/` | Large raw solver/runtime outputs. | No |
| `tmp/` | Temporary scratch outputs. | No |
| `text_extracts/` | Local text extracted from papers for private review. | No |

## Retention Rule

Commit compact, reproducible outputs that can support figures, tables, and
design decisions. Do not commit large raw solver files, extracted full texts,
or third-party article content.

For each committed result folder, include a short README explaining:

1. Why the result was generated.
2. Which script generates it.
3. Which files are manuscript-ready.
4. Which assumptions limit the result.
