# Results and tests cleanup review

Reviewed on 20 November 2026. The main readability problem is that working examples, historical iterations, provenance, and packaged reviews are all visible together.

## Changes made

- [Results guide](../results/README.md): a continuous reading order for the current food-editing case, the guided pilot, and component history.
- [Food-editing walkthrough](../results/phaseB_mask_review_20261120_01/README.md): links the original image through detection, masks, corrections, and generation outcomes.
- [Test guide](../tests/README.md): groups all 21 modules by pipeline stage and explains what passing checks mean.

## Clutter assessment

Approximate sizes include all files beneath each folder, measured during this review.

| Area | Observed size | Assessment |
| --- | --- | --- |
| `results/archive/` | 732 MiB, 22 files | Large historical review packages. Low priority for everyday reading, but not proven disposable. |
| `results/phase7_integration/` | 448 MiB, 1,208 files | Many iterations, reports, and ZIPs. Read its summary first; retain earlier failures as evidence. |
| `results/phaseB_mask_review_20261120_01/` | 637 MiB, 169 files | Current case split across stage folders. The new walkthrough supplies the missing order. |
| `results/phase9_pilot/` | 133 MiB, 163 files | Multiple runs and development records. Start with its report and `run_002` for the saved verification evidence. |
| `results/phase9_repeatability/` | 73 MiB, 157 files | Earlier pilot preparation and provenance. The pilot packaging code explicitly references files here. |
| `tests/` | 21 test modules | Distinct coverage areas, with shared fixture imports. No module established as unnecessary by this review. |

All ZIP files under `results/` were compared by SHA-256. No byte-identical ZIP duplicates were found. Similar names or overlapping contents alone do not establish that an archive can be deleted.

## What can be simplified later

Generated `__pycache__` folders can be recreated by Python and are already ignored by Git. Old review ZIPs are candidates for a separate backup location once their contents and references have been reconciled. Baseline source snapshots, failed attempts, manifests, and approval records should be assessed as research evidence, even if they are not used in the presentation.

Moving experiment folders requires updating recorded paths and reproduction instructions. Moving test modules requires updating shared fixture imports; the pilot packager also names particular test files. No historical results or test modules were removed or relocated in this cleanup.

For daily work and the presentation, navigate through the new results and test guides. Open raw iterations and logs only when explaining a specific result or failure.
