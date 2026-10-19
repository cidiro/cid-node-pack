# Cid Node Pack

Cid Node Pack is a custom node collection for
[ComfyUI](https://github.com/comfyanonymous/ComfyUI). It adds small workflow
building blocks for file handling, metadata extraction, JSON/YAML utilities,
wildcards, simple state/control-flow helpers, image and mask operations, and
local LLM prompt/chat helpers.

## What Is Included

- Image and media helpers: save images, reload/load images or videos from
  directories, concatenate image batches, apply masks, resize masks, and crop
  and stitch.
- Metadata tools: extract image, video, audio, and generic workflow metadata.
- Text and data utilities: concatenate strings, check string contents, manage
  string lists, join paths, and read/write JSON or YAML.
- Workflow state helpers: counters, global variables, any-value buffers,
  queues, lists, synchronization, timers, and storage nodes.
- Control helpers: boolean multiplexers/demultiplexers, trigger timing nodes,
  and type assertions.
- Prompt and LLM helpers: wildcard processing, system prompt handling, chat
  (with optional schema-constrained JSON output via `response_format`), and
  unload controls.

## Project Layout

- `nodes/` contains the ComfyUI node implementations.
- `js/` contains frontend extensions used by selected nodes.
- `utils/` contains shared Python helpers.
- `resources/` contains runtime support data.
- `tests/` contains focused tests for utility behavior.
- `__init__.py` registers the node classes and display names for ComfyUI.

## Installation

Place this repository inside your ComfyUI `custom_nodes` directory, then restart
ComfyUI:

```bash
cd ComfyUI/custom_nodes
git clone <this-repository-url> cid-node-pack
```

After restart, the nodes appear in ComfyUI with display names ending in
`(Cid)`.

## Wildcards

`Wildcard Processor (Cid)` resolves `__name__` references from the directory in
the `CID_WILDCARDS_DIR` environment variable. If the variable is unset, it uses
the `wildcards/` folder inside this pack. Set the variable before starting
ComfyUI:

```bash
export CID_WILDCARDS_DIR=/path/to/wildcards
```

## Timers

`Timer Start (Cid)` and `Timer Stop (Cid)` measure the wall-clock time that
elapses between two points in a workflow. Give both nodes the same
`timer_name`, splice `Timer Start` into the data path at point A and
`Timer Stop` at point B (both pass their input through unchanged). `Timer
Stop` returns the elapsed seconds as `FLOAT` and a formatted `STRING`,
prints the measurement to the ComfyUI console, and shows it on the node as
a digital clock: ghost segments before the first run, a live count-up while
the queue executes, and the frozen result afterwards. The precise value can
be copied from the console log.

Notes:

- The measurement is the wall-clock time between the two nodes' executions;
  it includes everything that runs in between, not only GPU compute.
- If the nodes between the pair are cache-hit on a re-queue, the elapsed
time is correctly near zero.
- Several `Timer Stop` nodes can read the same `Timer Start` (split timing).
- Reusing a `timer_name` across different open workflows in the same
  ComfyUI session shares state; use distinct names per workflow.

## Development

Node registration lives in `__init__.py`. When adding a node, create the module
under `nodes/`, import the class in `__init__.py`, and add it to
`NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.

Run the test suite from the repository root:

```bash
pytest
```
