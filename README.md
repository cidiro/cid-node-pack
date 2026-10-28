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

## Structured metadata extraction

`Extract Metadata (Cid)` returns normalized JSON by default for images and videos.
Gelbooru fields are directly accessible, so `JSON Get (Cid)` can use plain keys
such as `tags`, `width`, `height`, or `uploaded_at`:

```json
{
  "schema_version": 2,
  "post_id": 4632336,
  "tags": ["1girl", "bare_shoulders"],
  "width": 1091,
  "height": 1440,
  "uploaded_at": "2019-03-03T04:30:22Z",
  "resized": false,
  "metadata": {}
}
```

This example shows only part of the available data. Extraction keeps all post
fields and tags, with arrays, numbers, and booleans preserved as JSON types.
The node reads the downloader's JSON record from image/MP4 XMP or WebM container
tags. Existing downloads work without modifying the files. Older version-1
records are normalized to the same flat dimension fields and UTC upload dates;
`uploaded_at_raw` retains the original timestamp and
`metadata.gelbooru_schema_version` identifies the embedded record version.
Unknown dates or dates without a timezone keep only their raw value. Root
`width` and `height` come from the actual image or video stream, even if the
embedded saved dimensions are stale.

Other information is grouped under `metadata`: `image` holds Pillow information,
`exif` contains decoded EXIF fields, `xmp` contains the remaining parsed XMP, and
videos retain `format` and `streams`. Binary values such as ICC profiles become
`{"byte_length": 588}` summaries; no XML packets or escaped Python byte dumps
appear in normalized output. ComfyUI `prompt` and `workflow` JSON is parsed into
objects. Original captions, languages, attribution and other metadata remain
available here; the image or video itself is never changed.

Valid record values take precedence over individual Gelbooru fields, followed
by standard keyword/title/description fields. Invalid JSON or XMP falls back to
remaining readable metadata, with a short message in `metadata.warnings`.
Missing values remain absent; empty tag lists, zero scores and `false` survive.
XML DTD/entity declarations and packets larger than 8 MiB are rejected.

The optional `output_mode` input defaults to `normalized`. Select `raw` to get
the previous Pillow/ffprobe output when an existing workflow needs it. Audio
extraction keeps its previous ffprobe output in either mode. The legacy image
and video extraction classes use the same helpers. No additional dependencies
or runtime network access are required; video extraction uses ffprobe, enabling
XMP export for MP4 in normalized mode.

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
elapses between two points in a workflow. Give both nodes the same `id`,
splice `Timer Start` into the data path at point A and `Timer Stop` at
point B (both pass their `passthrough` input through unchanged). `Timer
Stop` shows the elapsed time on the node as a digital clock — ghost
segments before the first run, a live count-up while the queue executes,
and the frozen result afterwards — and prints the precise, copyable value
to the ComfyUI console.

Notes:

- The measurement is the wall-clock time between the two nodes' executions;
  it includes everything that runs in between, not only GPU compute.
- If the nodes between the pair are cache-hit on a re-queue, the elapsed
time is correctly near zero.
- Several `Timer Stop` nodes can read the same `Timer Start` (split timing).
- Reusing an `id` across different open workflows in the same ComfyUI
  session shares state; use distinct ids per workflow.

## Development

Node registration lives in `__init__.py`. When adding a node, create the module
under `nodes/`, import the class in `__init__.py`, and add it to
`NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.

Run the test suite from the repository root:

```bash
pytest
```
