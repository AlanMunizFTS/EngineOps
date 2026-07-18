# Project-Type Templates

Reference folder structures per project domain. Consulted when starting a new
project or restructuring an existing one — not needed in every session.

## Python vision inspection systems (camera + PLC comms + DB)

```
project_name/
├── pyproject.toml
├── config/{settings.yaml, logging.yaml}
├── src/project_name/
│   ├── acquisition/       # camera capture layer
│   ├── plc/                # PLC comms, isolated by design (see CLAUDE.md §6)
│   ├── inference/           # model loading, pre/post-processing
│   ├── pipeline/             # orchestration: acquisition→inference→plc→db
│   ├── db/                   # PostgreSQL access layer (repository pattern)
│   └── core/                  # shared types, exceptions, constants
├── tests/{unit/, integration/}   # integration mocks PLC/camera for cycle-time regression
├── scripts/                       # one-off diagnostics, calibration tools
└── docs/
```

Isolating the `plc/` module boundary is what makes bugs like an `asyncio.run()`-in-daemon-
thread event-loop conflict (encountered in the Dragonfly project) reproducible and unit-
testable without live hardware.

## Mixed-language FPGA/embedded builds (VHDL + HLS + C + Python)

Structure by language/target boundary, not by feature:

```
profiler_fpga/
├── hdl/{src/, testbench/, constraints/}    # VHDL
├── hls/{src/, testbench/}                   # Vitis HLS C++ kernels
├── firmware/                                  # bare-metal C
├── cm4_coprocessor/src/                        # Python async coprocessor (same layout as above)
├── scripts/tcl/                                 # build/synthesis automation
├── sim/                                          # GHDL/GTKWave outputs — gitignored
└── docs/timing_budget.md                          # critical for timing/encoder sync
```

Keep synthesis artifacts and `sim/` out of version control. Treat Tcl build scripts as
first-class code — modular, parameterized, not copy-pasted per board revision.

## Omron Sysmac Studio / IEC 61131-3 (PLC-side, ST)

Lives inside Sysmac's own project structure — "folders" apply to function block library
organization:

- Organize POUs by responsibility, not by station: `FB_VisionInspection`,
  `FB_CameraTrigger`, `FB_PLCHandshake` as reusable, parameterized function blocks — not one
  FB per physical station copy-pasted with different tag names.
- Scope global variable tables by domain (vision, safety, HMI) rather than one flat table.
- Export `.smc2` alongside a text-diffable XML export for real Git diffs on logic changes.
- Mirror Python-side FSM state names into ST state constants for consistency across the
  PLC/vision interface — avoid tag-mapping bugs from naming drift.

## Jetson-targeted CV pipelines (2D anomaly detection → 3D point cloud)

Split dev/training from edge runtime from the start:

```
inspection_system/
├── training/{datasets/, train.py, export_onnx.py}   # full framework, not deployed to edge
├── edge/{inference_engine.py, requirements-edge.txt, Dockerfile.jetson}  # minimal runtime
├── pointcloud/{generator.py, io_ply.py}
└── shared/                                            # types/schemas used by both
```

**Rule:** `edge/` never imports from `training/` — keeps the Jetson deployment lean (no
training-stack dependencies shipped to an AGX Orin with limited storage/thermal headroom).
