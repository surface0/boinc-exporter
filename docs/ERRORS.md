# ERRORS

## Grafana barchart: per-host bars stacked by project

- **Goal**: Change panels 9/10 into horizontal bars where each host is a bar and projects are stacked within it.
- **Attempt 1 (failed)**: Used `labelsToFields` (mode: columns, valueLabel: project). On Grafana v13 all rows collapsed into a single row, so the whole thing became one bar with everything stacked (no per-instance row split).
- **Attempt 2 (failed)**: Used `partitionByValues` (fields: ["project"], keepFields: false) only. Hosts split onto their own axis, but every frame's value field was still named `Value`. When barchart joined by instance, the same-named fields collided, so only one project showed up per host.
- **Attempt 3 (failed)**: Added `naming: { asLabels: true }` to `partitionByValues`. Still only one project stacked. Root cause: `partitionByValues` produces a separate frame per project, and Grafana barchart can only stack a single wide frame — with multiple frames it renders just the first one (the legend also showed only one project).
- **Fix (works)**: Three-stage transformation: `organize` (exclude Time) -> `partitionByValues` (fields: ["project"], keepFields: false, naming.asLabels: true) -> **`joinByField` (byField: "instance", mode: "outer")**. Partition splits per project, then join merges those frames into one wide frame keyed on instance, so barchart stacks all projects.
- **Value labels**: barchart has no inside/outside placement option for segment values. Set `showValue: "never"` and rely on tooltip/legend instead.
- **Lesson**: To get "category axis = label A / stacking = label B" in barchart you need a single wide frame. `partitionByValues` alone leaves multiple frames and is not enough — always follow it with `joinByField`. Always verify the result in the Grafana UI.
