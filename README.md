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
  queues, lists, synchronization, and storage nodes.
- Control helpers: boolean multiplexers/demultiplexers, trigger timing nodes,
  and type assertions.
- Prompt and LLM helpers: wildcard processing, system prompt handling, chat,
  and unload controls.

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

## Tolerant JSON Parsing

The JSON nodes recover slightly malformed input instead of failing the
workflow. Parsing goes through several layers: markdown fences and
surrounding prose are stripped, common LLM mistakes are repaired (unescaped
newlines or tabs inside string values, single or smart quotes, trailing
commas, Python `True`/`False`/`None`, stray or missing brackets), and the
input is finally tried as YAML. Brackets and quotes inside string values are
protected content and never counted as structure. `JSON Add (Cid)` and
`JSON Append (Cid)` go one step further: when the base object still cannot
be recovered (for example an LLM reply that is plain prose), they log a
warning and continue with an empty object.

## Wildcards

`Wildcard Processor (Cid)` resolves `__name__` references from the directory in
the `CID_WILDCARDS_DIR` environment variable. If the variable is unset, it uses
the `wildcards/` folder inside this pack. Set the variable before starting
ComfyUI:

```bash
export CID_WILDCARDS_DIR=/path/to/wildcards
```

## Development

Node registration lives in `__init__.py`. When adding a node, create the module
under `nodes/`, import the class in `__init__.py`, and add it to
`NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.

Run the test suite from the repository root:

```bash
pytest
```
